import json
import re
import sys
from typing import Any


def get_repo_path(job):
    repo = job["repository"]
    repo_name = repo["name"]
    owner = repo["owner"]
    return f"{owner}/{repo_name}"


def msg(msg, *args, **kwargs):
    if args or kwargs:
        if args:
            args = tuple(redact_sensitive_input(arg) for arg in args)
        if kwargs:
            kwargs = redact_sensitive_input(kwargs)
        msg = msg.format(*args, **kwargs)
    print(msg, file=sys.stderr)
    try:
        with open("/var/log/check", "a") as f:
            f.write("msg:" + msg + "\n")
    except PermissionError:
        pass


def looks_like_secret(key: str):
    """Return True if a dict key name (not its value) suggests a secret."""
    if not isinstance(key, str):
        return False

    # Split acronym-to-word and lower/digit-to-uppercase boundaries.
    key = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", key)
    key = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key)
    parts = re.findall(r"[a-z0-9]+", key.casefold())
    secret_parts = {"token", "secret", "key", "pem", "psk", "crt"}
    return any(part in secret_parts for part in parts)


def redact_sensitive_input(input_data) -> Any:
    if isinstance(input_data, dict):
        return {
            key: (
                "[REDACTED]"
                if looks_like_secret(key)
                else redact_sensitive_input(value)
            )
            for key, value in input_data.items()
        }
    if isinstance(input_data, list):
        return [redact_sensitive_input(value) for value in input_data]
    if isinstance(input_data, tuple):
        return tuple(redact_sensitive_input(value) for value in input_data)
    return input_data


def write_file(filepath, data):
    if data is None:  # pragma: no cover
        return
    if filepath.endswith(".json"):
        with open(filepath, "w") as file:
            json.dump(data, file)
    else:
        with open(filepath, "w") as file:
            file.write(data)
