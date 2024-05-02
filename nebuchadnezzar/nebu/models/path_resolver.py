import os
from pathlib import Path
from typing import Callable, Union, Iterable, Optional

from .book_container import BookContainer


class PathResolver:
    def __init__(
        self,
        book_container: BookContainer,
        module_path_getter: Callable[
            [BookContainer], Iterable[Union[Path, str]]
        ],
        module_id_getter: Callable[[str], Optional[str]],
    ):
        self.book_container = book_container
        self.collection_paths_by_book = {
            book.slug: os.path.realpath(
                os.path.join(
                    book_container.books_root, os.path.basename(book.href)
                )
            )
            for book in book_container.books
        }
        self.module_paths_by_id = {
            module_id: p
            for module_id, p in (
                (module_id_getter(p), p)
                for p in map(str, module_path_getter(book_container))
            )
            if module_id is not None
        }

    def get_collection_path(self, book_slug: str) -> str:
        collection = self.collection_paths_by_book.get(book_slug, None)
        assert collection is not None, f"Collection not found: {book_slug}"
        return collection

    def get_module_path(self, module_id: str) -> str:
        module = self.module_paths_by_id.get(module_id, None)
        assert module is not None, f"Module not found: {module_id}"
        return module

    def get_public_interactives_path(self, interactives_id: str, *parts: str):
        return os.path.join(
            self.book_container.root_dir,
            self.book_container.public_root,
            interactives_id,
            *parts
        )

    def get_private_interactives_path(self, interactives_id: str, *parts: str):
        return os.path.join(
            self.book_container.root_dir,
            self.book_container.private_root,
            os.path.basename(self.book_container.public_root),
            interactives_id,
            *parts
        )

    def find_interactives_paths(self, interactives_id, *parts: str):
        return {
            k: v for k, v in (
                (
                    "public",
                    self.get_public_interactives_path(interactives_id, *parts)
                ),
                (
                    "private",
                    self.get_private_interactives_path(interactives_id, *parts)
                )
            )
            if os.path.exists(v)
        }

    def find_interactives_path(self, interactives_id: str, *parts: str):
        paths = self.find_interactives_paths(interactives_id, *parts)
        return paths.get("public", paths.get("private", None))
