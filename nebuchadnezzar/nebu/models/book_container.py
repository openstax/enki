import os
from dataclasses import dataclass
from typing import List, Optional

from ..xml_utils import etree_from_str


CONTAINER_NSMAP = {
    "bk": "https://openstax.org/namespaces/book-container",
}


def parse_book_vars(etree):
    bk_vars = etree.xpath("//bk:var", namespaces=CONTAINER_NSMAP)
    bk_vars_by_name = {}

    for el in bk_vars:
        name = el.attrib["name"].strip()
        value = el.attrib["value"].strip()
        assert name, "Expected book var name, got empty string"
        assert value, "Expected book var value, got empty string"
        bk_vars_by_name[name.lower()] = value
    return bk_vars_by_name


def parse_books(etree):
    books = []
    for book in etree.xpath("//bk:book", namespaces=CONTAINER_NSMAP):
        kwargs = {
            k: v.strip()
            for k, v in (
                (k, book.attrib.get(k.replace("_", "-"), None))
                for k in Book.__dataclass_fields__.keys()
            )
            if v is not None
        }
        assert all(
            v != "" for v in kwargs.values()
        ), "Missing required value for book"
        books.append(Book(**kwargs))
    return books


def book_container_factory(
    default_books_root: str,
    default_pages_root: str,
    default_media_root: str,
    default_private_root: str,
    default_public_root: str,
):
    @dataclass
    class BookContainer:
        root_dir: str
        books: List["Book"]
        books_root: str = default_books_root
        pages_root: str = default_pages_root
        media_root: str = default_media_root
        private_root: str = default_private_root
        public_root: str = default_public_root

        def __post_init__(self):
            self.books_root = os.path.realpath(
                f"{self.root_dir}/{self.books_root}"
            )
            self.pages_root = os.path.realpath(
                f"{self.root_dir}/{self.pages_root}"
            )
            self.media_root = os.path.realpath(
                f"{self.root_dir}/{self.media_root}"
            )
            self.private_root = os.path.realpath(
                f"{self.root_dir}/{self.private_root}"
            )
            self.public_root = os.path.realpath(
                f"{self.root_dir}/{self.public_root}"
            )

        @classmethod
        def from_str(cls, xml_str: str, root_dir: str):
            etree = etree_from_str(xml_str)
            return cls(
                root_dir=root_dir,
                books=parse_books(etree),
                **parse_book_vars(etree)
            )

    return BookContainer


@dataclass
class Book:
    slug: str
    style: str
    href: str
    collection_id: Optional[str] = None


BookContainer = book_container_factory(
    "/collections",
    "/modules",
    "/media",
    "/private",
    "/interactives",
)
