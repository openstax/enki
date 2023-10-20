import os
import re
from pathlib import Path
from typing import Callable, Union, Iterable

from .book_container import BookContainer


def _search_path(p, pattern):
    match = re.search(pattern, str(p))
    assert match is not None, f'"{pattern}" not found in "{p}"'
    return match


def path_resolver_factory(
    module_path_getter: Callable[[BookContainer], Iterable[Union[Path, str]]],
    module_id_pattern: str,
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
                _search_path(p, module_id_pattern).group(0): str(p)
                for p in module_path_getter(book_container)
            }

        def get_collection_path(self, book_slug: str) -> str:
            return self._collection_paths_by_book[book_slug]

        def get_module_path(self, module_id: str) -> str:
            return self._module_paths_by_id[module_id]

    return PathResolver


PathResolver = path_resolver_factory(
    lambda container: Path(container.pages_root).glob("**/*.cnxml"), r"m[0-9]+"
)
