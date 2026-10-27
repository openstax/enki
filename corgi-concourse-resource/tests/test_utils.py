import pytest

from corgi_concourse_resource import utils


@pytest.mark.parametrize(
    "key",
    ["github_token", "authToken", "APIKey", "private-key", "clientSecret"],
)
def test_looks_like_secret_matches_secret_components(key):
    assert utils.looks_like_secret(key)


@pytest.mark.parametrize("key", ["monkey", "keyboard", "tokenize", "book_title"])
def test_looks_like_secret_ignores_partial_matches(key):
    assert not utils.looks_like_secret(key)


def test_redact_sensitive_input_recurses_without_mutating_input():
    input_data = {
        "source": {
            "github_token": "github-secret",
            "api_root": "https://example.test/api",
        },
        "jobs": [
            {"refreshToken": "refresh-secret", "status": "queued"},
        ],
        "other_values": ({"APIKey": "api-secret"}, "safe value"),
    }

    redacted = utils.redact_sensitive_input(input_data)

    assert redacted == {
        "source": {
            "github_token": "[REDACTED]",
            "api_root": "https://example.test/api",
        },
        "jobs": [
            {"refreshToken": "[REDACTED]", "status": "queued"},
        ],
        "other_values": ({"APIKey": "[REDACTED]"}, "safe value"),
    }
    assert input_data["source"]["github_token"] == "github-secret"


def test_msg_redacts_format_arguments(capsys, monkeypatch):
    def deny_log_file_write(*args, **kwargs):
        raise PermissionError

    monkeypatch.setattr(utils, "open", deny_log_file_write, raising=False)

    utils.msg(
        "Input: {}",
        {"source": {"github_token": "github-secret"}},
    )

    captured = capsys.readouterr()
    assert "github-secret" not in captured.err
    assert "[REDACTED]" in captured.err


def test_msg_redacts_format_keyword_arguments(capsys, monkeypatch):
    def deny_log_file_write(*args, **kwargs):
        raise PermissionError

    monkeypatch.setattr(utils, "open", deny_log_file_write, raising=False)

    utils.msg("Token: {github_token}", github_token="github-secret")

    captured = capsys.readouterr()
    assert "github-secret" not in captured.err
    assert "[REDACTED]" in captured.err
