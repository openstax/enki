"""Inject / modify metadata for book CNXML from git"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree
from pygit2 import Repository
from .profiler import timed

NS_MDML = "http://cnx.rice.edu/mdml"
NS_CNXML = "http://cnx.rice.edu/cnxml"
NS_COLLXML = "http://cnx.rice.edu/collxml"
GIT_SHA_PREFIX_LEN = 7

@timed
def remove_metadata_entries(xml_doc, old_metadata, md_namespace):
    metadata = xml_doc.xpath(
        "//x:metadata",
        namespaces={"x": md_namespace}
    )[0]

    for tag in old_metadata:
        element = metadata.xpath(
            f"./md:{tag}",
            namespaces={"md": NS_MDML}
        )
        if element:
            metadata.remove(element[0])

@timed
def add_metadata_entries(xml_doc, new_metadata, md_namespace):
    """Insert metadata entries from dictionairy into document"""
    metadata = xml_doc.xpath(
        "//x:metadata",
        namespaces={"x": md_namespace}
    )[0]

    for tag, value in new_metadata.items():
        element = etree.Element(f"{{{NS_MDML}}}{tag}")
        element.text = value
        element.tail = "\n"
        metadata.append(element)

@timed
def determine_book_version(reference, repo, commit):
    """Determine the book version string given a reference, a git repo, and
    a target a commit"""
    # We want to check if the provided reference is a tag that matches the
    # target commit. Otherwise, we will either select a unique associated tag,
    # or if all else fails fallback to the first few characters of the commit
    # sha
    matching_tags = [
        ref.shorthand for ref in repo.references.objects
        if ref.name.startswith("refs/tags") and ref.target == commit.id
    ]

    if reference in matching_tags:
        # The provided reference matches a tag for the commit
        return reference

    # If the provided reference isn't a matching tag, but a single matching tag
    # was identified, return it.
    if len(matching_tags) == 1:
        return matching_tags[0]

    # Fallback to returning a version based on commit sha in all other cases
    return str(commit.id)[0:GIT_SHA_PREFIX_LEN]

@timed
def main():
    git_repo = Path(sys.argv[1]).resolve(strict=True)
    modules_dir = Path(sys.argv[2]).resolve(strict=True)
    collections_dir = Path(sys.argv[3]).resolve(strict=True)
    reference = sys.argv[4]
    canonical_file = Path(sys.argv[5]).resolve(strict=True)
    repo = Repository(git_repo)

    canonical_list = json.load(canonical_file.open())

    canonical_mapping = {}

    for bookslug in reversed(canonical_list):
        collection = collections_dir / f'{bookslug}.collection.xml'
        col_tree = etree.parse(str(collection))
        col_modules = col_tree.xpath(
            "//col:module/@document", namespaces={"col": NS_COLLXML})
        col_uuid = col_tree.xpath(
            "//md:uuid", namespaces={"md": NS_MDML})[0].text
        for module in col_modules:
            canonical_mapping[module] = col_uuid

    # For the time being, we're going to parse the timestamp of the HEAD
    # commit and use that as the revised time for all module pages.
    commit = repo.revparse_single('HEAD')
    revised_time = datetime.fromtimestamp(
        commit.commit_time,
        timezone.utc
    ).isoformat()
    book_version = determine_book_version(reference, repo, commit)

    # Get list of module files while filtering orphans using canonical_mapping
    module_files = [
        mf.resolve(strict=True) for mf in modules_dir.glob("**/*")
        if mf.is_file() and mf.name == "index.cnxml" and mf.parent.name in canonical_mapping
    ]

    collection_files = [
        cf.resolve(strict=True) for cf in collections_dir.glob("*.xml")
    ]

    for module_file in module_files:
        cnxml_doc = etree.parse(str(module_file))

        remove_metadata_entries(cnxml_doc, ["canonical-book-uuid"], NS_CNXML)

        new_metadata = {
            "revised": revised_time,
            "canonical-book-uuid": canonical_mapping[module_file.parent.name]
        }
        add_metadata_entries(cnxml_doc, new_metadata, NS_CNXML)

        with open(module_file, "wb") as f:
            cnxml_doc.write(f, encoding="utf-8", xml_declaration=False)

    for collection_file in collection_files:
        collection_doc = etree.parse(str(collection_file))
        new_metadata = {
            "revised": revised_time,
            "version": book_version
        }
        add_metadata_entries(collection_doc, new_metadata, NS_COLLXML)

        with open(collection_file, "wb") as f:
            collection_doc.write(f, encoding="utf-8", xml_declaration=False)


if __name__ == "__main__":  # pragma: no cover
    main()
