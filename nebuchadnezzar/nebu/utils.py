import re
import os
from typing import Optional, Sequence
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


def recursive_merge(
    lhs,
    rhs,
    *,
    merge_sequence=lambda lhs, rhs: lhs + rhs,
    default=lambda lhs, rhs: rhs
):
    if isinstance(lhs, dict):
        return lhs | rhs | {
            k: recursive_merge(
                lhs[k], rhs[k], merge_sequence=merge_sequence, default=default
            )
            for k in set(lhs.keys()) & set(rhs.keys())
        }
    elif isinstance(lhs, Sequence):
        return merge_sequence(lhs, rhs)
    return default(lhs, rhs)
