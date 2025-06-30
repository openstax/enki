from contextlib import contextmanager
from dataclasses import dataclass
import re
import sys
from typing import Any

from lxml import etree

from . import secret_patterns


_secret_patterns = [
    entry["regex"] for entry in secret_patterns.patterns
] + [
    r"bearer [a-zA-Z0-9_\-.]+",  # Bearer tokens
]

_secret_name_patterns = [
    "secret",
    "token",
    "key",
    "pass",
    "password",
    "passphrase",
    "pin",
    "auth",
    "credential",
    "cert",
    "cipher",
    "encryption",
    "private",
    "secure",
    "jwt",
]

_all_patterns = _secret_name_patterns + _secret_patterns


def _log(*msgs: str):
    print(*msgs, file=sys.stderr)


def _looks_like_secret(name: str, value: Any):
    return any(
        pat in v or re.search(pat, v, flags=re.I)
        for pat in _all_patterns
        for v in (name, repr(value), str(value))
    )


def _safe_value(name: str, value: Any):
    if isinstance(value, dict):
        return {k: _safe_value(k, v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return [_safe_value("", v) for v in value]
    elif _looks_like_secret(name, value):
        return "*" * 24
    else:
        return value


@dataclass
class Local:
    name: str
    value: Any

    @property
    def safe_value(self):
        return _safe_value(self.name, self.value)


class HookAttachmentGroup:
    def __init__(self, excepthook):
        self._excepthook = excepthook
        self._original_hook = None

    def attach(self, sys):
        self._original_hook = sys.excepthook
        sys.excepthook = self._excepthook
        return self

    def detach(self, sys):
        original_hook = self._original_hook
        assert original_hook, "Detach called before attach"
        sys.excepthook = original_hook
        return self


def _handle_tracebacks(tracebacks, handle_locals):
    for i, tb_part in enumerate(tracebacks):
        frame = tb_part.tb_frame
        tb_line = tb_part.tb_lineno
        filename = frame.f_code.co_filename
        function = frame.f_code.co_name
        frame_locals = frame.f_locals

        _log(f"\n### Stack Frame {len(tracebacks) - i} ###")
        _log(f"Function: {function}")
        _log(f"File: {filename}, Line {tb_line}")

        handle_locals(
            [Local(name=k, value=v) for k, v in frame_locals.items()]
        )


def make_hook(handle_locals):
    def enhanced_traceback(exc_type, exc_value, tb):  # pragma: no cover
        tracebacks = []
        tb_part = tb
        # Walk through all frames until we hit None
        while tb_part is not None:
            tracebacks.append(tb_part)
            tb_part = tb_part.tb_next
        _handle_tracebacks(tracebacks, handle_locals)
        raise exc_type(exc_value).with_traceback(tb)

    return enhanced_traceback


def _describe_element(value) -> str:
    # Search up and down the tree for nearest data-sm
    nearest_sm_search = value.xpath(
        "ancestor-or-self::*[@data-sm]/@data-sm | .//*[@data-sm]/@data-sm"
    )
    parts = {
        "tag": getattr(value, "tag", None),
        "nearest-data-sm": nearest_sm_search[0] if nearest_sm_search else None,
    }
    return repr({k: v for k, v in parts.items() if v})


def default_handle_locals(frame_locals: list[Local]):
    if not frame_locals:
        return

    max_len = 500
    _log("Local Variables:")
    for local in frame_locals:
        name = local.name
        if isinstance(local.value, (etree._Element, etree._ElementTree)):
            printable_value = _describe_element(local.value)
        else:
            printable_value = repr(local.safe_value)
        if len(printable_value) >= max_len:
            printable_value = f"{printable_value[:max_len]}..."
        _log(f"    {name} = {printable_value}")


@contextmanager
def attach_hook(excepthook, sys):
    """
    Context manager for temporarily replacing the exception hook.

    Args:
        excepthook: The new exception handler function
        sys: The sys module instance to modify

    Yields:
        HookAttachmentGroup instance after attaching the hook
    """
    group = HookAttachmentGroup(excepthook).attach(sys)
    try:
        yield group
    finally:
        group.detach(sys)


default_attach = HookAttachmentGroup(make_hook(default_handle_locals))


def attach(sys):
    """Attach the default exception hook."""
    return default_attach.attach(sys)


def detach(sys):
    """Detach the default exception hook and restore original."""
    return default_attach.detach(sys)
