import re
import os
from typing import Optional
from contextlib import contextmanager
from time import time
import inspect
import logging


PKG_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
logger = logging.getLogger("nebuchadnezzar")


@contextmanager
def unknown_progress(msg):
    caller = inspect.stack()[2]
    fq_pkg = ".".join(
        os.path.relpath(os.path.splitext(caller.filename)[0], PKG_ROOT).split(
            os.sep
        )
    )
    trace = f"[{fq_pkg}:{caller.lineno}]"
    logger.info(f"{trace} {msg}...")
    start = time()
    yield
    logger.info(
        f"{trace} "
        f"Finished {msg[0].lower()}{msg[1:]} in {round(time() - start, 2)}s"
    )


def re_first_or_default(
    pattern: str, s: str, default: Optional[str] = None
) -> Optional[str]:
    match = re.search(pattern, s)
    return match.group(0) if match is not None else default


def merge_by_index(lhs, rhs, merge_sequence, default):
    return list(
        recursive_merge(
            dict(enumerate(lhs)),
            dict(enumerate(rhs)),
            merge_sequence=merge_sequence,
            default=default,
        ).values()
    )


def recursive_merge(
    lhs,
    rhs,
    *,
    merge_sequence=merge_by_index,
    default=lambda lhs, rhs: rhs if rhs is not None else lhs
):
    if isinstance(lhs, dict) and isinstance(rhs, dict):
        return lhs | rhs | {
            k: recursive_merge(
                lhs[k], rhs[k], merge_sequence=merge_sequence, default=default
            )
            for k in set(lhs.keys()) & set(rhs.keys())
        }
    elif isinstance(lhs, (list, tuple)) and isinstance(rhs, (list, tuple)):
        return merge_sequence(lhs, rhs, merge_sequence, default)
    return default(lhs, rhs)


def try_parse_bool(maybe_bool):
    result = None
    if isinstance(maybe_bool, bool):
        result = maybe_bool
    elif isinstance(maybe_bool, str):
        str_correctness = maybe_bool.strip().lower()
        if str_correctness in ("true", "false"):
            result = str_correctness == "true"
    elif isinstance(maybe_bool, (float, int)):
        result = maybe_bool > 0
    assert result is not None, f"Failed to parse bool from: {maybe_bool}"
    return result
