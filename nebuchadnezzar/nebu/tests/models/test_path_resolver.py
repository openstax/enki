import os

from nebu.utils import re_first_or_default
from nebu.models.path_resolver import PathResolver
from nebu.models.book_container import book_container_factory, Book
import pytest


BookContainer = book_container_factory(
    "/collections",
    "/modules",
    "/media",
    "/private",
    "/interactives",
)

module_id_map = {
    "m1234": "a/b/c/m1234",
    "m4567": "a/b/c/m4567",
    "m8910": "a/b/c/m8910",
}


@pytest.fixture
def test_collection_href():
    return "../collections/test.collection.xml"


@pytest.fixture
def test_container(test_collection_href):
    return BookContainer(
        "/made/up/abs/path".replace('/', os.sep),
        [
            Book(
                "book-slug1", "dummy", test_collection_href
            )
        ],
    )


@pytest.fixture
def test_resolver(test_container):
    return PathResolver(
        test_container,
        lambda _: list(module_id_map.values()),
        lambda s: re_first_or_default(r'm[0-9]+', s)
    )


def test_resolve_module_id(test_resolver):
    for k, v in module_id_map.items():
        assert test_resolver.get_module_path(k) == v


def test_resolve_book_slug(test_container, test_resolver, test_collection_href):
    p = test_resolver.get_collection_path("book-slug1")
    assert p == os.path.join(
        test_container.books_root,
        os.path.basename(test_collection_href)
    )


def test_resolve_interactive_id(test_container, test_resolver, test_collection_href):
    public = test_resolver.get_public_interactives_path("abc123").replace(os.sep, '/')
    private = test_resolver.get_private_interactives_path("abc123").replace(os.sep, '/')
    assert public == f"{test_container.root_dir}/interactives/abc123"
    assert private == f"{test_container.root_dir}/private/interactives/abc123"
