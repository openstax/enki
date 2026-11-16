import io
import json
from unittest.mock import MagicMock, Mock

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

MISSING = object()


def mock_response(cookies=None, json_data=None, error=None):
    response = Mock(spec=requests.Response)
    response.text = "{}"
    response.cookies = cookies or {}
    response.json.return_value = json_data or {}
    if error:
        response.raise_for_status.side_effect = error
    return response


def mock_session(monkeypatch, login_response, put_response):
    session = MagicMock(spec=requests.Session)
    session.cookies = requests.cookies.RequestsCookieJar()
    session.__enter__.return_value = session
    session.__exit__.return_value = False
    session_cookie_on_put = []

    def login(*args, **kwargs):
        session.cookies.update(login_response.cookies)
        return login_response

    def put(url, json):
        session_cookie_on_put.append(session.cookies.get("session"))
        return put_response

    session.get.side_effect = login
    session.put.side_effect = put
    monkeypatch.setattr(corgi_api.requests, "Session", lambda: session)
    return session, session_cookie_on_put


def test_update_job_logs_in_and_reuses_session_cookie(monkeypatch):
    login_response = mock_response(cookies={"session": "session-cookie"})
    put_response = mock_response(json_data={"id": "123"})
    session, session_cookie_on_put = mock_session(
        monkeypatch, login_response, put_response
    )
    monkeypatch.setattr(corgi_api, "msg", lambda *args, **kwargs: None)

    result = corgi_api.update_job(
        "https://corgi.example/api",
        "123",
        {"status_id": "5"},
        "github-token",
    )

    assert result == {"id": "123"}
    session.get.assert_called_once_with(
        "https://corgi.example/api/auth/token-login",
        headers={"Authorization": "Bearer github-token"},
    )
    session.put.assert_called_once_with(
        "https://corgi.example/api/jobs/123", json={"status_id": "5"}
    )
    assert session_cookie_on_put == ["session-cookie"]


def test_update_job_strips_github_token_before_login(monkeypatch):
    session, _ = mock_session(
        monkeypatch,
        mock_response(cookies={"session": "session-cookie"}),
        mock_response(json_data={"id": "123"}),
    )
    monkeypatch.setattr(corgi_api, "msg", lambda *args, **kwargs: None)

    corgi_api.update_job(
        "https://corgi.example/api", "123", {}, "  github-token\n"
    )

    session.get.assert_called_once_with(
        "https://corgi.example/api/auth/token-login",
        headers={"Authorization": "Bearer github-token"},
    )


@pytest.mark.parametrize(
    "github_token", ["", " \t\n", 12345, {"token": "invalid"}]
)
def test_update_job_rejects_missing_or_invalid_github_token(
    monkeypatch, github_token
):
    session_calls = []
    monkeypatch.setattr(
        corgi_api.requests,
        "Session",
        lambda: session_calls.append("created"),
    )

    with pytest.raises(
        ValueError, match="github_token must be a non-empty string"
    ):
        corgi_api.update_job(
            "https://corgi.example/api", "123", {}, github_token
        )

    assert session_calls == []


def test_update_job_does_not_put_when_login_fails(monkeypatch):
    login_response = mock_response(error=requests.HTTPError("401 Unauthorized"))
    session, _ = mock_session(monkeypatch, login_response, mock_response())
    monkeypatch.setattr(corgi_api, "msg", lambda *args, **kwargs: None)

    with pytest.raises(requests.HTTPError, match="401 Unauthorized"):
        corgi_api.update_job(
            "https://corgi.example/api", "123", {}, "github-token"
        )

    session.put.assert_not_called()


def test_update_job_raises_when_put_fails(monkeypatch):
    session, _ = mock_session(
        monkeypatch,
        mock_response(cookies={"session": "session-cookie"}),
        mock_response(error=requests.HTTPError("500 Server Error")),
    )
    monkeypatch.setattr(corgi_api, "msg", lambda *args, **kwargs: None)

    with pytest.raises(requests.HTTPError, match="500 Server Error"):
        corgi_api.update_job(
            "https://corgi.example/api",
            "123",
            {"status_id": "5"},
            "github-token",
        )

    session.put.assert_called_once()


def test_update_job_does_not_put_when_login_sets_no_session_cookie(
    monkeypatch,
):
    session, _ = mock_session(monkeypatch, mock_response(), mock_response())
    monkeypatch.setattr(corgi_api, "msg", lambda *args, **kwargs: None)

    with pytest.raises(RuntimeError, match="did not set a session cookie"):
        corgi_api.update_job(
            "https://corgi.example/api", "123", {}, "github-token"
        )

    session.put.assert_not_called()


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


@pytest.mark.parametrize(
    "source_token, expected",
    [
        ("  github-token\n", "  github-token\n"),
        ("github-token", "github-token"),
    ],
)
def test_out_forwards_valid_github_token(
    tmp_path, monkeypatch, source_token, expected
):
    assert (
        run_out_and_capture_token(tmp_path, monkeypatch, source_token)
        == expected
    )


@pytest.mark.parametrize("source_token", [MISSING, None, "", " \t\n", 12345])
def test_out_rejects_missing_or_invalid_github_token(
    tmp_path, monkeypatch, source_token
):
    with pytest.raises(
        ValueError,
        match="github_token is required in the resource source",
    ):
        run_out_and_capture_token(tmp_path, monkeypatch, source_token)


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
