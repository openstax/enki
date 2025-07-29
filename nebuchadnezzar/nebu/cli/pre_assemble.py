"""Inject / modify metadata for book CNXML from git"""

from pathlib import Path
from datetime import timezone
from typing import Optional
import os
import logging
import uuid

import click
from lxml import etree
from lxml.builder import ElementMaker
from git import Repo

from ._common import common_params
from ..utils import re_first_or_default, unknown_progress
from ..models.book_container import CONTAINER_NSMAP, BookContainer
from ..models.path_resolver import PathResolver
from ..models.book_part import BookPart
from ..parse import NSMAP as CNXML_NSMAP
from ..xml_utils import Elementish, etree_to_str, open_xml


NS_MDML = CNXML_NSMAP["md"]
NS_COLLXML = CNXML_NSMAP["col"]
NS_CNXML = CNXML_NSMAP["c"]
NS_BOOK = CONTAINER_NSMAP["bk"]
GIT_SHA_PREFIX_LEN = 7


logger = logging.getLogger("nebuchadnezzar")


def check_for_existing_metadata(xml_doc, tags, sourcefile):
    existing = xml_doc.xpath(
        "|".join(f"//md:{tag}" for tag in tags), namespaces={"md": NS_MDML}
    )
    assert (
        len(existing) == 0
    ), f"Unexpectedly found one of ({', '.join(tags)}) in {sourcefile}"


def add_metadata_entries(xml_doc, new_metadata, md_namespace):
    """Insert metadata entries from dictionairy into document"""
    metadata = xml_doc.xpath("//x:metadata", namespaces={"x": md_namespace})[0]

    for tag, value in new_metadata.items():
        element = etree.Element(f"{{{NS_MDML}}}{tag}")
        element.text = value
        element.tail = "\n"
        metadata.append(element)


def fetch_update_metadata(
    path_resolver,
    canonical_mapping,
    git_repo,
):
    repo = Repo(git_repo)

    # For the time being, we're going to parse the timestamp of the HEAD
    # commit and use that as the revised time for all module pages.
    commit = repo.head.commit
    revised_time = commit.committed_datetime.astimezone(
        timezone.utc
    ).isoformat()
    book_version = str(commit.hexsha)[0:GIT_SHA_PREFIX_LEN]

    module_ids_by_path = {
        v: k for k, v in path_resolver.module_paths_by_id.items()
    }

    # Get list of module files while filtering orphans using canonical_mapping
    module_files = [
        module_file
        for module_id, module_file in path_resolver.module_paths_by_id.items()
        if module_id in canonical_mapping
    ]

    collection_files = list(path_resolver.collection_paths_by_book.values())

    for module_file in module_files:
        cnxml_doc = open_xml(module_file)

        check_for_existing_metadata(
            cnxml_doc, ["revised", "canonical-book-uuid"], module_file
        )

        new_metadata = {
            "revised": revised_time,
            "canonical-book-uuid": canonical_mapping[
                module_ids_by_path[module_file]
            ],
        }
        add_metadata_entries(cnxml_doc, new_metadata, NS_CNXML)

        with open(module_file, "wb") as f:
            cnxml_doc.write(f, encoding="utf-8", xml_declaration=False)

    for collection_file in collection_files:
        collection_doc = open_xml(collection_file)
        check_for_existing_metadata(
            collection_doc, ["revised", "version"], collection_file
        )
        new_metadata = {"revised": revised_time, "version": book_version}
        add_metadata_entries(collection_doc, new_metadata, NS_COLLXML)

        with open(collection_file, "wb") as f:
            collection_doc.write(f, encoding="utf-8", xml_declaration=False)


def patch_paths(container, path_resolver, canonical_mapping):
    media_dir_name = os.path.basename(container.media_root)
    base_src_query = (
        "//c:{tag_name}[@src]["
        '   not(starts-with(@src, "http://") or starts-with(@src, "https://"))'
        "]"
    )
    res_query = "//c:link[@resource]"
    src_query = "|".join(
        (
            base_src_query.format(tag_name="iframe"),
            base_src_query.format(tag_name="image"),
            base_src_query.format(tag_name="flash"),
            base_src_query.format(tag_name="object"),
        )
    )

    for module_id, module_file in path_resolver.module_paths_by_id.items():
        if module_id not in canonical_mapping:
            continue
        cnxml_doc = open_xml(module_file)
        for query, attr_name in ((src_query, "src"), (res_query, "resource")):
            for node in cnxml_doc.xpath(query, namespaces=CNXML_NSMAP):
                src = node.attrib[attr_name]
                parts = Path(src).parts
                if media_dir_name not in parts:
                    logger.info(f"Skipping {src}")
                    continue
                media_dir_name_idx = parts.index(media_dir_name) + 1
                new_src = os.path.relpath(
                    os.path.join(
                        container.media_root,
                        *parts[media_dir_name_idx:],
                    ),
                    os.path.dirname(module_file),
                )
                if new_src != src:
                    logger.info(f'Patching src "{src}" -> "{new_src}"')
                    node.attrib[attr_name] = new_src
        with open(module_file, "wb") as f:
            cnxml_doc.write(f, encoding="utf-8", xml_declaration=False)


def looks_like_super_document(p: str):
    with open(p, "rb") as fin:
        # should see the word super in the first KiB of the doc
        return b"super" in fin.read(1 << 10)


def make_super_collection(module_uuid: str, module_id: str) -> Elementish:
    E = ElementMaker(
        namespace=NS_COLLXML, nsmap={None: NS_COLLXML, "md": NS_MDML}
    )
    col_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, module_uuid))
    metadata = E("metadata", E(f"{{{NS_MDML}}}uuid", col_uuid))
    content = E("content", E("module", document=module_id))
    collection = E("collection", metadata, content)
    return collection


def get_repo_context(input_dir: str):
    books_xml = Path(input_dir) / "META-INF" / "books.xml"
    container = BookContainer.from_str(books_xml.read_bytes(), input_dir)
    path_resolver = PathResolver(
        container,
        lambda container: Path(container.pages_root).glob("**/*.cnxml"),
        lambda s: re_first_or_default(r"m[0-9]+", s),
    )
    return container, path_resolver, books_xml


def remove_super_documents(
    container: BookContainer, path_resolver: PathResolver, query: str
):
    for book in container.books:
        collection = path_resolver.get_collection_path(book.slug)
        col_tree = open_xml(collection)
        super_modules = col_tree.xpath(query, namespaces={"col": NS_COLLXML})
        # Only update collection files if we need to
        if super_modules:
            for elem in super_modules:
                parent = elem.getparent()
                parent.remove(elem)
            with open(collection, "wb") as f:
                col_tree.write(f, encoding="utf-8", xml_declaration=False)


def create_super_collections(
    container: BookContainer, super_documents_by_id: dict[str, BookPart]
):
    collection_paths = []

    for module_id, doc in super_documents_by_id.items():
        module_uuid = doc.metadata["uuid"]
        assert (
            module_uuid is not None
        ), f"Expected module uuid for: {module_id}"
        super_collection = make_super_collection(module_uuid, module_id)
        super_collection_path = os.path.join(
            container.books_root, f"super-{module_uuid}.collection.xml"
        )
        with open(super_collection_path, "wb") as f:
            f.write(etree_to_str(super_collection))

        collection_paths.append(super_collection_path)

    return collection_paths


def append_super_collections_to_container(
    container: BookContainer, books_xml: Path, collection_paths: list[str]
):
    # TODO: maybe need to use a different style
    super_style = "dummy"
    container_tree = etree.parse(books_xml)
    # Should always find one since we literally just parsed it
    container_elem = container_tree.xpath(
        "//bk:container", namespaces={"bk": NS_BOOK}
    )[0]
    for collection_path in collection_paths:
        collection_name = os.path.basename(collection_path)
        href = os.path.relpath(collection_path, container.books_root)
        slug = os.path.splitext(collection_name)[0].replace(".collection", "")
        book = etree.Element(
            f"{{{NS_BOOK}}}book", slug=slug, style=super_style, href=href
        )
        container_elem.append(book)
    with books_xml.open("wb") as f:
        container_tree.write(f, encoding="utf-8", xml_declaration=False)


def handle_super_documents(
    container: BookContainer, path_resolver: PathResolver, books_xml: Path
):
    super_documents_by_id = {
        module_id: doc
        for module_id, doc in (
            (module_id, BookPart.doc_from_file(path))
            for module_id, path in path_resolver.module_paths_by_id.items()
            if looks_like_super_document(path)
        )
        if doc.is_super
    }

    # Step 0: Run away if there are no super documents to handle
    if not super_documents_by_id:
        return

    query = "|".join(
        f'//col:module[@document="{module_id}"]'
        for module_id in super_documents_by_id.keys()
    )

    # Step 1: Remove super documents from normal collections
    remove_super_documents(container, path_resolver, query)

    # Step 2: Create new collections for each super document
    collection_paths = create_super_collections(
        container, super_documents_by_id
    )

    # Step 3: Add collections to container
    append_super_collections_to_container(
        container, books_xml, collection_paths
    )


@click.command(name="pre-assemble")
@common_params
@click.argument("input-dir", type=click.Path(exists=True))
@click.option("--repo-dir", default=None, type=Optional[str])
def pre_assemble(input_dir, repo_dir):
    """Prepares litezip structure data for single-page-html file conversion."""

    canonical_mapping = {}

    with unknown_progress("Handling super documents"):
        handle_super_documents(*get_repo_context(input_dir))

    # Re-read the context since we modified the container
    container, path_resolver, _ = get_repo_context(input_dir)

    with unknown_progress("Mapping documents"):
        for book in container.books:
            collection = path_resolver.get_collection_path(book.slug)
            col_tree = open_xml(collection)
            col_modules = col_tree.xpath(
                "//col:module/@document", namespaces={"col": NS_COLLXML}
            )
            col_uuid = col_tree.xpath("//md:uuid", namespaces={"md": NS_MDML})[
                0
            ].text
            for module in col_modules:
                canonical_mapping[module] = col_uuid

    git_repo = (
        Path(repo_dir).resolve(strict=True)
        if repo_dir is not None
        else input_dir
    )
    with unknown_progress("Updating metadata"):
        fetch_update_metadata(
            path_resolver,
            canonical_mapping,
            git_repo,
        )

    # NOTE: For now we are patching image links incase modules are moved up
    #       a directory and their links are not updated to match the new path.
    #       Hopefully this is temporary.
    with unknown_progress("Patching resource paths"):
        patch_paths(container, path_resolver, canonical_mapping)
