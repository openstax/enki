import io
import json

import pytest
import requests

from corgi_concourse_resource import corgi_api, out


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
