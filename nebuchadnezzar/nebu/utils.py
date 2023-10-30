import re
from typing import Optional


def re_first_or_default(
    pattern: str, s: str, default: Optional[str] = None
) -> Optional[str]:
    match = re.search(pattern, s)
    return match.group(0) if match is not None else default
