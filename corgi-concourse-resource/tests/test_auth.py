import io
import json

import pytest
import requests
import vcr

from corgi_concourse_resource import check, corgi_api, in_, out


def request_header(request, header_name):
    for name, value in request.headers.items():
        if name.lower() == header_name.lower():
            return value[0] if isinstance(value, (list, tuple)) else value
    return None


def session_headers_matcher(request1, request2):
    for header_name in ("Authorization", "Cookie", "Content-Type"):
        assert request_header(request1, header_name) == request_header(
            request2, header_name
        )


auth_vcr = vcr.VCR(match_on=("method", "uri", "body", "session_headers"))
auth_vcr.register_matcher("session_headers", session_headers_matcher)


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


def test_update_job_sends_real_session_cookie(monkeypatch):
    monkeypatch.setattr(corgi_api, "msg", lambda *args, **kwargs: None)

    with auth_vcr.use_cassette(
        "tests/cassettes/test_update_job_session_cookie.yaml",
        record_mode="none",
    ) as cassette:
        result = corgi_api.update_job(
            "http://localhost/api",
            "123",
            {"status_id": "5"},
            "github-token",
        )

    assert result == {"id": 123, "status_id": "5"}
    assert cassette.all_played


def test_update_job_calls_token_login(monkeypatch):
    monkeypatch.setattr(corgi_api, "msg", lambda *args, **kwargs: None)

    with (
        auth_vcr.use_cassette(
            "tests/cassettes/test_update_job_calls_token_login.yaml",
            record_mode="none",
        ) as cassette,
        pytest.raises(requests.HTTPError) as error,
    ):
        corgi_api.update_job(
            "http://localhost/api", "123", {"status_id": "5"}, None
        )

    assert error.value.response.status_code == 401
    assert cassette.all_played
