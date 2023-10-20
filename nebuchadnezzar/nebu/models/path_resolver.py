import os
import re
from pathlib import Path
from typing import Callable, Union, Iterable, Optional
from functools import partial

from .book_container import BookContainer


def _first_or_none(pattern: str, s: str) -> Optional[str]:
    match = re.search(pattern, str(s))
    return match.group(0) if match is not None else None


def path_resolver_factory(
    module_path_getter: Callable[[BookContainer], Iterable[Union[Path, str]]],
    module_id_getter: Callable[[str], Optional[str]],
):
    class PathResolver:
        def __init__(self, book_container: BookContainer):
            self._collection_paths_by_book = {
                book.slug: os.path.realpath(
                    os.path.join(
                        book_container.books_root, os.path.basename(book.href)
                    )
                )
                for book in book_container.books
            }
            self._module_paths_by_id = {
                module_id: p
                for module_id, p in (
                    (module_id_getter(p), p)
                    for p in map(str, module_path_getter(book_container))
                )
                if module_id is not None
            }

        def get_collection_path(self, book_slug: str) -> str:
            return self._collection_paths_by_book[book_slug]

        def get_module_path(self, module_id: str) -> str:
            return self._module_paths_by_id[module_id]

    return PathResolver


PathResolver = path_resolver_factory(
    lambda container: Path(container.pages_root).glob("**/*.cnxml"),
    partial(_first_or_none, r"m[0-9]+")
)
