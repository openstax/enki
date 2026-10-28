import io
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
import requests

from corgi_concourse_resource import check, corgi_api, in_, out


class FakeResponse:
    text = "{}"

    def __init__(self, cookies=None, json_data=None, error=None):
        self.cookies = cookies or {}
        self.json_data = json_data or {}
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        return self.json_data


class FakeSession:
    def __init__(self, login_response, put_response):
        self.login_response = login_response
        self.put_response = put_response
        self.cookies = {}
        self.get_calls = []
        self.put_calls = []
        self.session_cookie_on_put = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, headers):
        self.get_calls.append((url, headers))
        session_cookie = self.login_response.cookies.get("session")
        if session_cookie:
            self.cookies["session"] = session_cookie
        return self.login_response

    def put(self, url, json):
        self.put_calls.append((url, json))
        self.session_cookie_on_put = self.cookies.get("session")
        return self.put_response


def test_out_forwards_github_token(tmp_path, monkeypatch):
    token = "github-token"
    payload = {
        "source": {
            "api_root": "https://corgi.example/api",
            "github_token": token,
        },
        "params": {"id": "id", "status_id": "5"},
    }
    (tmp_path / "id").write_text("123")
    forwarded = {}

    def update_job(api_root, job_id, data, github_token=None):
        forwarded.update(
            api_root=api_root,
            job_id=job_id,
            data=data,
            github_token=github_token,
        )
        return {"id": job_id}

    monkeypatch.setattr(out, "msg", lambda *args, **kwargs: None)
    monkeypatch.setattr(out, "update_job", update_job)

    result = out.out(str(tmp_path), io.StringIO(json.dumps(payload)))

    assert result == {"version": {"id": "123"}}
    assert forwarded["github_token"] == token
    assert forwarded["api_root"] == "https://corgi.example/api"


def test_update_job_without_token_still_updates(monkeypatch):
    session = FakeSession(FakeResponse(), FakeResponse(json_data={"id": "123"}))
    monkeypatch.setattr(corgi_api.requests, "Session", lambda: session)
    monkeypatch.setattr(corgi_api, "msg", lambda *args, **kwargs: None)

    result = corgi_api.update_job(
        "https://corgi.example/api",
        "123",
        {"status_id": "5"},
    )

    assert result == {"id": "123"}
    assert session.get_calls == []
    assert session.put_calls == [
        ("https://corgi.example/api/jobs/123", {"status_id": "5"})
    ]


def test_update_job_logs_in_and_reuses_session_cookie(monkeypatch):
    login_response = FakeResponse(cookies={"session": "session-cookie"})
    put_response = FakeResponse(json_data={"id": "123"})
    session = FakeSession(login_response, put_response)
    monkeypatch.setattr(corgi_api.requests, "Session", lambda: session)
    monkeypatch.setattr(corgi_api, "msg", lambda *args, **kwargs: None)

    result = corgi_api.update_job(
        "https://corgi.example/api",
        "123",
        {"status_id": "5"},
        "github-token",
    )

    assert result == {"id": "123"}
    assert session.get_calls == [
        (
            "https://corgi.example/api/auth/token-login",
            {"Authorization": "Bearer github-token"},
        )
    ]
    assert session.put_calls == [
        ("https://corgi.example/api/jobs/123", {"status_id": "5"})
    ]
    assert session.session_cookie_on_put == "session-cookie"


def test_update_job_does_not_put_when_login_fails(monkeypatch):
    login_response = FakeResponse(error=requests.HTTPError("401 Unauthorized"))
    session = FakeSession(login_response, FakeResponse())
    monkeypatch.setattr(corgi_api.requests, "Session", lambda: session)
    monkeypatch.setattr(corgi_api, "msg", lambda *args, **kwargs: None)

    with pytest.raises(requests.HTTPError, match="401 Unauthorized"):
        corgi_api.update_job(
            "https://corgi.example/api", "123", {}, "github-token"
        )

    assert not session.put_calls


def test_update_job_raises_when_put_fails(monkeypatch):
    session = FakeSession(
        FakeResponse(cookies={"session": "session-cookie"}),
        FakeResponse(error=requests.HTTPError("500 Server Error")),
    )
    monkeypatch.setattr(corgi_api.requests, "Session", lambda: session)
    monkeypatch.setattr(corgi_api, "msg", lambda *args, **kwargs: None)

    with pytest.raises(requests.HTTPError, match="500 Server Error"):
        corgi_api.update_job(
            "https://corgi.example/api",
            "123",
            {"status_id": "5"},
            "github-token",
        )

    assert len(session.put_calls) == 1


def test_update_job_does_not_put_when_login_sets_no_session_cookie(
    monkeypatch,
):
    session = FakeSession(FakeResponse(), FakeResponse())
    monkeypatch.setattr(corgi_api.requests, "Session", lambda: session)
    monkeypatch.setattr(corgi_api, "msg", lambda *args, **kwargs: None)

    with pytest.raises(RuntimeError, match="did not set a session cookie"):
        corgi_api.update_job(
            "https://corgi.example/api", "123", {}, "github-token"
        )

    assert not session.put_calls


def run_out_and_capture_token(tmp_path, monkeypatch, source_token):
    source = {"api_root": "https://corgi.example/api"}
    if source_token is not MISSING:
        source["github_token"] = source_token
    payload = {"source": source, "params": {"id": "id", "status_id": "5"}}
    (tmp_path / "id").write_text("123")
    forwarded = {}

    def update_job(api_root, job_id, data, github_token=None):
        forwarded["github_token"] = github_token
        return {"id": job_id}

    monkeypatch.setattr(out, "msg", lambda *args, **kwargs: None)
    monkeypatch.setattr(out, "update_job", update_job)
    out.out(str(tmp_path), io.StringIO(json.dumps(payload)))
    return forwarded["github_token"]


MISSING = object()


@pytest.mark.parametrize(
    "source_token, expected",
    [
        (MISSING, None),
        (None, None),
        ("", None),
        ("   ", None),
        (12345, None),
        ("  github-token\n", "github-token"),
    ],
)
def test_out_normalizes_github_token(
    tmp_path, monkeypatch, source_token, expected
):
    assert (
        run_out_and_capture_token(tmp_path, monkeypatch, source_token)
        == expected
    )


def test_check_does_not_use_github_token(monkeypatch):
    calls = []

    def get_jobs(*args, **kwargs):
        calls.append((args, kwargs))
        return [{"id": 7}]

    monkeypatch.setattr(check, "msg", lambda *args, **kwargs: None)
    monkeypatch.setattr(check, "get_jobs", get_jobs)
    payload = {
        "source": {
            "api_root": "https://corgi.example/api",
            "status_id": 1,
            "github_token": "github-token",
        }
    }

    assert check.check(io.StringIO(json.dumps(payload))) == [{"id": 7}]
    assert calls == [(("https://corgi.example/api",), {"status_id": 1})]


def test_in_does_not_use_github_token(tmp_path, monkeypatch):
    calls = []
    job = {
        "repository": {"owner": "openstax", "name": "osbooks-test"},
        "version": None,
        "books": [{"slug": "test-book"}],
    }

    def get_job(*args, **kwargs):
        calls.append((args, kwargs))
        return job

    monkeypatch.setattr(in_, "msg", lambda *args, **kwargs: None)
    monkeypatch.setattr(corgi_api, "get_job", get_job)
    payload = {
        "source": {
            "api_root": "https://corgi.example/api",
            "github_token": "github-token",
        },
        "version": {"id": "123"},
    }

    result = in_.in_(str(tmp_path), io.StringIO(json.dumps(payload)))

    assert result == {"version": {"id": "123"}}
    assert calls == [(("https://corgi.example/api", "123"), {})]


class FakeCorgiHandler(BaseHTTPRequestHandler):
    requests_seen = []

    def log_message(self, *args):
        pass

    def respond(self, status, body, headers=()):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        for name, value in headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        self.requests_seen.append(("GET", self.path, self.headers))
        if self.headers.get("Authorization") == "Bearer github-token":
            self.respond(200, {}, [("Set-Cookie", "session=abc123; Path=/")])
        else:
            self.respond(401, {})

    def do_PUT(self):
        self.requests_seen.append(("PUT", self.path, self.headers))
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        if "session=abc123" in (self.headers.get("Cookie") or ""):
            self.respond(200, {"id": 123, **body})
        else:
            self.respond(401, {})


@pytest.fixture
def fake_corgi():
    FakeCorgiHandler.requests_seen = []
    server = HTTPServer(("127.0.0.1", 0), FakeCorgiHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/api", FakeCorgiHandler
    server.shutdown()
    server.server_close()
    thread.join()


def test_update_job_sends_real_session_cookie_over_http(
    monkeypatch, fake_corgi
):
    api_root, handler = fake_corgi
    monkeypatch.setattr(corgi_api, "msg", lambda *args, **kwargs: None)

    result = corgi_api.update_job(
        api_root, "123", {"status_id": "5"}, "github-token"
    )

    assert result == {"id": 123, "status_id": "5"}
    assert [(method, path) for method, path, _ in handler.requests_seen] == [
        ("GET", "/api/auth/token-login"),
        ("PUT", "/api/jobs/123"),
    ]
    put_headers = handler.requests_seen[1][2]
    assert put_headers["Content-Type"] == "application/json"
    assert "Authorization" not in put_headers


def test_update_job_without_token_is_rejected_by_server(
    monkeypatch, fake_corgi
):
    api_root, handler = fake_corgi
    monkeypatch.setattr(corgi_api, "msg", lambda *args, **kwargs: None)

    with pytest.raises(requests.HTTPError):
        corgi_api.update_job(api_root, "123", {"status_id": "5"})

    assert [method for method, _, _ in handler.requests_seen] == ["PUT"]
