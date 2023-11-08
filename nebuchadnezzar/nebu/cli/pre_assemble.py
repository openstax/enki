"""Inject / modify metadata for book CNXML from git"""

from pathlib import Path
from datetime import timezone
from typing import Optional

import click
from lxml import etree
from git import Repo

from ._common import common_params
from ..utils import re_first_or_default
from ..models.book_container import BookContainer
from ..models.path_resolver import PathResolver
from ..parse import NSMAP as CNXML_NSMAP
from ..xml_utils import open_xml


NS_MDML = CNXML_NSMAP["md"]
NS_COLLXML = CNXML_NSMAP["col"]
NS_CNXML = CNXML_NSMAP["c"]
GIT_SHA_PREFIX_LEN = 7


def remove_metadata_entries(xml_doc, old_metadata, md_namespace):
    metadata = xml_doc.xpath("//x:metadata", namespaces={"x": md_namespace})[0]

    for tag in old_metadata:
        element = metadata.xpath(f"./md:{tag}", namespaces=CNXML_NSMAP)
        if element:
            metadata.remove(element[0])


def add_metadata_entries(xml_doc, new_metadata, md_namespace):
    """Insert metadata entries from dictionairy into document"""
    metadata = xml_doc.xpath("//x:metadata", namespaces={"x": md_namespace})[0]

    for tag, value in new_metadata.items():
        element = etree.Element(f"{{{NS_MDML}}}{tag}")
        element.text = value
        element.tail = "\n"
        metadata.append(element)


def determine_book_version(reference, repo, commit):
    """Determine the book version string given a reference, a git repo, and
    a target a commit"""
    # We want to check if the provided reference is a tag that matches the
    # target commit. Otherwise, we will either select a unique associated tag,
    # or if all else fails fallback to the first few characters of the commit
    # sha
    matching_tags = [
        tag.name for tag in repo.tags if tag.commit.hexsha == commit.hexsha
    ]

    if reference in matching_tags:
        # The provided reference matches a tag for the commit
        return reference

    # If the provided reference isn't a matching tag, but a single matching tag
    # was identified, return it.
    if len(matching_tags) == 1:
        return matching_tags[0]

    # Fallback to returning a version based on commit sha in all other cases
    return str(commit.hexsha)[0:GIT_SHA_PREFIX_LEN]


def fetch_update_metadata(
    container,
    path_resolver,
    canonical_mapping,
    git_repo,
    reference,
):
    repo = Repo(git_repo)
    canonical_mapping = {}

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

    # For the time being, we're going to parse the timestamp of the HEAD
    # commit and use that as the revised time for all module pages.
    commit = repo.head.commit
    revised_time = commit.committed_datetime.astimezone(
        timezone.utc
    ).isoformat()
    book_version = determine_book_version(reference, repo, commit)

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

        remove_metadata_entries(cnxml_doc, ["canonical-book-uuid"], NS_CNXML)

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
        new_metadata = {"revised": revised_time, "version": book_version}
        add_metadata_entries(collection_doc, new_metadata, NS_COLLXML)

        with open(collection_file, "wb") as f:
            collection_doc.write(f, encoding="utf-8", xml_declaration=False)


@click.command(name="pre-assemble")
@common_params
@click.argument("input-dir", type=click.Path(exists=True))
@click.argument("reference", type=str)
@click.option("--repo-dir", default=None, type=Optional[str])
def pre_assemble(input_dir, reference, repo_dir):
    """Prepares litezip structure data for single-page-html file conversion."""

    books_xml = Path(input_dir) / "META-INF" / "books.xml"
    container = BookContainer.from_str(books_xml.read_bytes(), input_dir)
    path_resolver = PathResolver(
        container,
        lambda container: Path(container.pages_root).glob("**/*.cnxml"),
        lambda s: re_first_or_default(r"m[0-9]+", s),
    )

    canonical_mapping = {}

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
    fetch_update_metadata(
        container,
        path_resolver,
        canonical_mapping,
        git_repo,
        reference,
    )
