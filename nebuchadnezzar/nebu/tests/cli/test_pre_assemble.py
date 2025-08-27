from pathlib import Path
from shutil import copytree, rmtree
from datetime import datetime, timezone
import json
from itertools import chain

import pytest

from nebu.cli.main import cli
from nebu.cli.pre_assemble import handle_super_documents
from nebu.models.book_container import BookContainer
from nebu.models.path_resolver import PathResolver
from nebu.utils import re_first_or_default
from nebu.xml_utils import open_xml
from nebu.parse import NSMAP as CNXML_NSMAP


MOCK_TAG_NAME = "my-mock-tag"
MD_MODULE = 0
MD_COLLECTION = 1
NS_COLLXML = CNXML_NSMAP["col"]
NS_MDML = CNXML_NSMAP["md"]


def prepare_directory(directory, tmp_path):
    output_dir = Path(tmp_path) / "pre-assemble"
    copytree(directory, output_dir)
    # Remove existing metadata from this copy of the test data
    # This metadata is required for other tests, but it causes problems here
    for f in chain(*map(output_dir.glob, ("**/*.cnxml", "**/*.xml"))):
        tree = open_xml(f)
        metadata = tree.xpath('//*[local-name() = "metadata"]')
        if len(metadata) == 0:
            continue
        metadata_el = metadata[0]
        for el in metadata_el.xpath(
            "//md:revised | //md:version | //md:canonical-book-uuid",
            namespaces=CNXML_NSMAP,
        ):
            metadata_el.remove(el)
        with open(f, "wb") as fout:
            tree.write(fout, encoding="utf-8", xml_declaration=False)
    return output_dir


@pytest.fixture
def tmp_book_dir(datadir, tmp_path):
    src_data = datadir / "collection_for_git_workflow"
    return prepare_directory(src_data, tmp_path)


@pytest.fixture
def tmp_book_dir_with_super(datadir, tmp_path):
    src_data = datadir / "collection_for_git_workflow_with_super"
    return prepare_directory(src_data, tmp_path)


@pytest.fixture
def current_snapshot_dir(snapshot_dir):
    return snapshot_dir / "pre-assemble"


@pytest.fixture
def repo_mock(mocker):
    repo_mock = mocker.MagicMock()
    commit_mock = repo_mock().head.commit
    commit_mock.committed_datetime = datetime.fromtimestamp(
        0.0, tz=timezone.utc
    )
    commit_mock.hexsha = "0000000"
    return repo_mock


def parse_metadata(book_dir):
    books_xml = book_dir / "META-INF" / "books.xml"

    container = BookContainer.from_str(books_xml.read_bytes(), str(book_dir))
    path_resolver = PathResolver(
        container,
        lambda container: Path(container.pages_root).glob("**/*.cnxml"),
        lambda s: re_first_or_default(r"m[0-9]+", s),
    )

    for thing_type, resolver_dict, selector in (
        (
            MD_MODULE,
            path_resolver.module_paths_by_id,
            "//md:revised | //md:canonical-book-uuid",
        ),
        (
            MD_COLLECTION,
            path_resolver.collection_paths_by_book,
            "//md:revised | //md:version",
        ),
    ):
        for thing_id, path in resolver_dict.items():
            tree = open_xml(path)
            metadata = tree.xpath(selector, namespaces=CNXML_NSMAP)
            yield (
                thing_type,
                [
                    {"tag": el.tag, "line": el.sourceline, "text": el.text}
                    for el in metadata
                ],
                thing_id,
            )


def test_pre_assemble_cmd_no_tags(
    repo_mock, mocker, assert_match, invoker, tmp_book_dir
):
    # GIVEN: A valid repository

    # WHEN: pre-assemble is called with a ref
    args = ["pre-assemble", str(tmp_book_dir)]
    mocker.patch("nebu.cli.pre_assemble.Repo", repo_mock)
    result = invoker(cli, args)

    # THEN:
    #   The exit code is 0 (success)
    #   Modules contained in a collection are updated with git metadata
    #   Modules not contained in a collection are left alone (m50000)
    #   The commit sha is used
    assert result.exit_code == 0, result.output
    for thing_type, metadata, thing_id in parse_metadata(tmp_book_dir):
        assert_match(
            json.dumps(metadata, indent=2),
            f"{thing_id}-metadata.json",
            use_func_name=thing_type != MD_MODULE,
        )

    rmtree(tmp_book_dir)


def test_pre_assemble_patch_paths(
    repo_mock, mocker, assert_match, invoker, tmp_book_dir
):
    # GIVEN: A valid repository

    # WHEN: pre-assemble is called
    args = ["pre-assemble", str(tmp_book_dir)]
    mocker.patch("nebu.cli.pre_assemble.Repo", repo_mock)
    result = invoker(cli, args)

    # THEN:
    #   The exit code is 0 (success)
    #   The module metadata remains unchanged
    assert result.exit_code == 0, result.output
    for thing_type, metadata, thing_id in parse_metadata(tmp_book_dir):
        assert_match(
            json.dumps(metadata, indent=2),
            f"{thing_id}-metadata.json",
            use_func_name=thing_type != MD_MODULE,
        )

    books_xml = tmp_book_dir / "META-INF" / "books.xml"

    container = BookContainer.from_str(
        books_xml.read_bytes(), str(tmp_book_dir)
    )
    path_resolver = PathResolver(
        container,
        lambda container: Path(container.pages_root).glob("**/*.cnxml"),
        lambda s: re_first_or_default(r"m[0-9]+", s),
    )
    module_path = path_resolver.module_paths_by_id["m46857"]
    tree = open_xml(module_path)
    media_dir_name = Path(container.media_root).name
    # GIVEN: media elements that were patched during pre-assemble step
    selectors = (
        # These two images have paths that should be updated
        '//c:image[../@id = "image-src-patch-test"]',
        '//c:iframe[../@id = "iframe-src-patch-test"]',
        # This image has a path that was already updated
        '//c:image[../@id = "image-src-no-patch-test"]',
        '//c:link[../@id = "link-resource-patch-test"]'
    )
    elements = tree.xpath("|".join(selectors), namespaces=CNXML_NSMAP)
    # WHEN: We find our test elements
    assert len(elements) == len(selectors), "Could not find test elements"
    for elm in elements:
        # Links use resource attrib, everything else uses src
        src = elm.attrib["src" if "src" in elm.attrib else "resource"]
        parts = Path(src).parts
        assert (
            media_dir_name in parts
        ), f"{src} link should include the media folder, but it does not"
        media_dir_name_idx = parts.index(media_dir_name) + 1
        media_dir_from_src = (
            Path(module_path).parent / Path(*parts[:media_dir_name_idx])
        ).resolve()
        # THEN: Path in src should point to media folder
        assert media_dir_from_src == Path(
            container.media_root
        ), f"{src} link should point to the media folder"
        assert media_dir_from_src.exists(), (
            f"Path pointed to by {src} does not exist; "
            f"directory contents: {[e.name for e in tmp_book_dir.iterdir()]}"
        )
        # THEN: Path should still include file name
        parent_id = elm.getparent().attrib["id"]
        name_by_parent_id = {
            "image-src-patch-test": "foobar.png",
            "iframe-src-patch-test": "index.html",
            "image-src-no-patch-test": "foobar.png",
            "link-resource-patch-test": "foobar.png",
        }
        assert (
            name_by_parent_id[parent_id] in src
        ), f"Part of the file path was lost in translation, {src}"

    rmtree(tmp_book_dir)


def test_handle_super_documents(tmp_book_dir_with_super, assert_match):
    books_xml = tmp_book_dir_with_super / "META-INF" / "books.xml"

    container = BookContainer.from_str(
        books_xml.read_bytes(), str(tmp_book_dir_with_super)
    )
    path_resolver = PathResolver(
        container,
        lambda container: Path(container.pages_root).glob("**/*.cnxml"),
        lambda s: re_first_or_default(r"m[0-9]+", s),
    )
    super_path = tmp_book_dir_with_super / "super"
    handle_super_documents(container, path_resolver, books_xml, super_path)
    all_documents = []
    for book in container.books:
        collection = path_resolver.get_collection_path(book.slug)
        col_tree = open_xml(collection)
        documents = col_tree.xpath(
            "//col:module/@document", namespaces={"col": NS_COLLXML}
        )
        all_documents.extend(documents)
    file_names = [p.name for p in tmp_book_dir_with_super.iterdir()]
    super_module_id = "m50001"
    super_doc_uuid = "0c641ba1-5fab-4a9b-b272-5b64cb45dce1"
    super_collection = next(
        (
            p for p in tmp_book_dir_with_super.iterdir()
            if super_doc_uuid in p.name
        ),
        None
    )
    super_doc_meta = super_path / f"{super_doc_uuid}.metadata.json"
    normal_collection = tmp_book_dir_with_super / "collection.xml"
    assert super_collection is not None
    assert super_collection.suffix == ".xml"
    assert all_documents and super_module_id not in all_documents
    assert 1 == sum(1 for name in file_names if super_doc_uuid in name)
    assert_match(books_xml.read_text(), books_xml.name)
    assert_match(super_collection.read_text(), super_collection.name)
    assert_match(normal_collection.read_text(), normal_collection.name)
    assert_match(super_doc_meta.read_text(), super_doc_meta.name)


def test_handle_super_documents_no_meta(tmp_book_dir_with_super, assert_match):
    books_xml = tmp_book_dir_with_super / "META-INF" / "books.xml"
    super_doc_uuid = "0c641ba1-5fab-4a9b-b272-5b64cb45dce1"
    super_module_id = "m50001"

    container = BookContainer.from_str(
        books_xml.read_bytes(), str(tmp_book_dir_with_super)
    )
    path_resolver = PathResolver(
        container,
        lambda container: Path(container.pages_root).glob("**/*.cnxml"),
        lambda s: re_first_or_default(r"m[0-9]+", s),
    )
    super_doc_path = path_resolver.get_module_path(super_module_id)
    super_doc = open_xml(super_doc_path)
    super_meta_elem = super_doc.xpath(
        '//md:super', namespaces={"md": NS_MDML}
    )[0]
    super_meta_elem.getparent().remove(super_meta_elem)
    super_doc.write(super_doc_path)
    super_path = tmp_book_dir_with_super / "super"
    handle_super_documents(container, path_resolver, books_xml, super_path)
    all_documents = []
    for book in container.books:
        collection = path_resolver.get_collection_path(book.slug)
        col_tree = open_xml(collection)
        documents = col_tree.xpath(
            "//col:module/@document", namespaces={"col": NS_COLLXML}
        )
        all_documents.extend(documents)
    file_names = [p.name for p in tmp_book_dir_with_super.iterdir()]
    super_collection = next(
        (
            p for p in tmp_book_dir_with_super.iterdir()
            if super_doc_uuid in p.name
        ),
        None
    )
    super_doc_meta = super_path / f"{super_doc_uuid}.metadata.json"
    assert super_collection is not None
    assert super_collection.suffix == ".xml"
    assert all_documents and super_module_id not in all_documents
    assert 1 == sum(1 for name in file_names if super_doc_uuid in name)
    assert_match(books_xml.read_text(), books_xml.name)
    assert_match(super_doc_meta.read_text(), super_doc_meta.name)
