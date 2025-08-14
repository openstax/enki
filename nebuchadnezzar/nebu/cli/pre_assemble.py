"""Inject / modify metadata for book CNXML from git"""

from dataclasses import dataclass
import json
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
from ..models.book_container import CONTAINER_NSMAP, Book, BookContainer
from ..models.path_resolver import PathResolver
from ..models.book_part import BookPart
from ..parse import NSMAP as CNXML_NSMAP, parse_metadata
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


@dataclass
class SuperDocument:
    module_id: str
    module_uuid: str
    original_book: Book
    original_collection_meta: dict
    parsed: BookPart
    collection_path: str

    @property
    def collection_name(self):
        return os.path.basename(self.collection_path)

    @property
    def slug(self):
        return os.path.splitext(self.collection_name)[0].replace(
            ".collection", ""
        )


def looks_like_super_document(p: str):
    with open(p, "rb") as fin:
        # should see the word "super" in the first KiB of the doc
        return b"super" in fin.read(1 << 10)


def make_super_collection(super_document: SuperDocument) -> Elementish:
    module_uuid = super_document.module_uuid
    module_id = super_document.module_id
    language = super_document.original_collection_meta["language"]
    language = language if isinstance(language, str) else "en"
    E = ElementMaker(
        namespace=NS_COLLXML, nsmap={None: NS_COLLXML, "md": NS_MDML}
    )
    col_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, module_uuid))
    title = super_document.parsed.metadata["title"]
    license_url = super_document.original_collection_meta["license_url"]
    license_text = super_document.original_collection_meta["license_text"]
    assert isinstance(title, str), "Invalid document title"

    metadata = E(
        "metadata",
        E(f"{{{NS_MDML}}}uuid", col_uuid),
        E(f"{{{NS_MDML}}}title", title),
        E(f"{{{NS_MDML}}}slug", super_document.slug),
        E(f"{{{NS_MDML}}}language", language),
    )
    if isinstance(license_url, str) and isinstance(license_text, str):
        license_el = E(f"{{{NS_MDML}}}license", license_text, url=license_url)
        metadata.append(license_el)
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
    container: BookContainer,
    path_resolver: PathResolver,
    super_documents_by_id: dict[str, BookPart],
):
    query = "|".join(
        f'//col:module[@document="{module_id}"]'
        for module_id in super_documents_by_id.keys()
    )
    super_documents = []

    for book in container.books:
        collection = path_resolver.get_collection_path(book.slug)
        col_tree = open_xml(collection)
        super_modules = col_tree.xpath(query, namespaces={"col": NS_COLLXML})
        # Only update collection files if we need to
        if super_modules:
            collection_meta = parse_metadata(col_tree)
            for elem in super_modules:
                module_id = elem.attrib["document"]
                document = super_documents_by_id[module_id]
                module_uuid = document.metadata["uuid"]
                assert isinstance(
                    module_uuid, str
                ), f"Expected module uuid for: {module_id}"
                parent = elem.getparent()
                parent.remove(elem)
                super_collection_path = os.path.join(
                    container.books_root, f"super-{module_uuid}.collection.xml"
                )
                super_document = SuperDocument(
                    module_id,
                    module_uuid,
                    book,
                    collection_meta,
                    document,
                    super_collection_path,
                )
                super_documents.append(super_document)
            with open(collection, "wb") as f:
                col_tree.write(f, encoding="utf-8", xml_declaration=False)

    return super_documents


def create_super_collections(super_documents: list[SuperDocument]):
    for super_document in super_documents:
        super_collection = make_super_collection(super_document)
        collection_path = super_document.collection_path
        with open(collection_path, "wb") as f:
            f.write(etree_to_str(super_collection))


def append_super_collections_to_container(
    books_xml: Path, super_documents: list[SuperDocument]
):
    # TODO: maybe need to use a different style
    super_style = "dummy"
    container_tree = etree.parse(books_xml)
    # Should always find one since we literally just parsed it
    container_elem = container_tree.xpath(
        "//bk:container", namespaces={"bk": NS_BOOK}
    )[0]
    for super_document in super_documents:
        collection_path = super_document.collection_path
        href = os.path.relpath(collection_path, books_xml.parent)
        slug = super_document.slug
        book = etree.Element(
            f"{{{NS_BOOK}}}book", slug=slug, style=super_style, href=href
        )
        container_elem.append(book)
    with books_xml.open("wb") as f:
        container_tree.write(f, encoding="utf-8", xml_declaration=False)


def save_super_metadata(
    super_path: Path, super_documents: list[SuperDocument]
):
    def _prepare_relation(tag, this_book_uuid, module_uuid):
        text = tag["text"]
        prefix = "https://openstax.org/orn"
        if text.startswith(prefix):
            orn = text
        else:
            if ":" in text:
                book, page = text.split(":")
                target_book_uuid = uuid.UUID(book)
                target_page_uuid = uuid.UUID(page)
            else:
                target_book_uuid = this_book_uuid
                target_page_uuid = uuid.UUID(text)
            orn = f"{prefix}/book:page/{target_book_uuid}:{target_page_uuid}"
        relation_uuid = str(
            uuid.uuid5(
                uuid.NAMESPACE_OID, f"{this_book_uuid}:{module_uuid}:{orn}"
            )
        )
        return (relation_uuid, tag["type"], orn)

    for doc in super_documents:
        module_uuid = doc.module_uuid
        out_path = super_path / f"{module_uuid}.metadata.json"
        doc_meta = doc.parsed.metadata
        super_meta = doc_meta["super_metadata"]
        abstract = doc_meta["abstract"]
        book_uuid = doc.original_collection_meta["uuid"]
        assert isinstance(super_meta, dict)
        super_meta["relations"] = [
            {"id": relation_uuid, "type": relation_type, "orn": orn}
            for relation_uuid, relation_type, orn in sorted(
                set(
                    _prepare_relation(tag, book_uuid, doc.module_uuid)
                    for tag in super_meta.pop("tags")
                )
            )
        ]

        meta = {
            "id": module_uuid,
            "name": doc_meta["title"],
            **({"description": abstract} if abstract else {}),
            **(super_meta if isinstance(super_meta, dict) else {}),
        }
        with out_path.open("w") as f:
            json.dump(meta, f, ensure_ascii=False)


def handle_super_documents(
    container: BookContainer,
    path_resolver: PathResolver,
    books_xml: Path,
    super_path: Path,
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

    super_path.mkdir(parents=True, exist_ok=True)

    # Step 1: Remove super documents from normal collections
    super_documents = remove_super_documents(
        container, path_resolver, super_documents_by_id
    )

    # Step 2: Create new collections for each super document
    create_super_collections(super_documents)

    # Step 3: Add collections to container
    append_super_collections_to_container(books_xml, super_documents)

    # Step 4: Save metadata for easy use later
    save_super_metadata(super_path, super_documents)


@click.command(name="pre-assemble")
@common_params
@click.argument("input-dir", type=click.Path(exists=True))
@click.option("--repo-dir", default=None, type=Optional[str])
@click.option("--super-dir", default=None, type=Optional[str])
def pre_assemble(input_dir, repo_dir, super_dir):
    """Prepares litezip structure data for single-page-html file conversion."""

    canonical_mapping = {}

    with unknown_progress("Handling super documents"):
        super_path = (
            Path(input_dir) / "super" if super_dir is None else Path(super_dir)
        )
        handle_super_documents(*get_repo_context(input_dir), super_path)

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
