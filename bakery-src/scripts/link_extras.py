"""
Replaces legacy module ids in links to external modules with
uuids from the target module and corresponding canonical book       .
"""

import json
import re
import sys
from urllib.parse import unquote
from .profiler import timed

import requests
from lxml import etree

MAX_RETRIES = 2


def load_canonical_list(canonical_list):
    with open(canonical_list) as canonical_file:
        canonical_books = json.load(canonical_file)["canonical_books"]
        canonical_ids = [book["uuid"] for book in canonical_books]

    return canonical_ids


@timed
def load_assembled_collection(input_dir):
    """load assembled collection"""
    assembled_collection = f"{input_dir}/collection.assembled.xhtml"
    return etree.parse(assembled_collection)


@timed
def find_legacy_id(link):
    """find legacy module id"""
    parsed = unquote(link)

    return re.search(r'\/contents\/(m\d{5})', parsed).group(1)


def init_requests_session(adapter):
    session = requests.Session()
    session.mount("https://", adapter)
    return session


@timed
def get_target_uuid(session, server, legacy_id):
    """get target module uuid"""
    response = session.get(
        f"https://{server}/content/{legacy_id}",
        allow_redirects=False
    )
    response.raise_for_status()

    return response.headers["Location"].split("/")[-1]


@timed
def get_containing_books(session, server, module_uuid):
    """get list of books containing module"""
    response = session.get(f"https://{server}/extras/{module_uuid}")
    response.raise_for_status()

    content = response.json()
    return [book["ident_hash"].split("@")[0] for book in content["books"]]


@timed
def gen_page_slug_resolver(session, server):
    """Generate a page slug resolver function"""

    book_tree_by_uuid = {}

    def _get_page_slug(book_uuid, page_uuid):
        """Get page slug from book"""

        def _parse_tree_for_slug(tree, page_uuid):
            """Recursively walk through tree to find page slug"""
            curr_slug = tree["slug"]
            curr_id = tree["id"]
            if curr_id == page_uuid:
                return curr_slug
            if "contents" in tree:
                for node in tree["contents"]:
                    slug = _parse_tree_for_slug(node, page_uuid)
                    if slug:
                        return slug
            return None

        cached_tree = book_tree_by_uuid.get(book_uuid)
        if cached_tree:
            book_metadata = cached_tree
        else:
            response = session.get(f"https://{server}/contents/{book_uuid}")
            response.raise_for_status()

            book_metadata = response.json()
            book_tree_by_uuid[book_uuid] = book_metadata

        page_slug = _parse_tree_for_slug(book_metadata["tree"], page_uuid)

        return page_slug

    return _get_page_slug


@timed
def match_canonical_book(canonical_ids, containing_books, module_uuid, link):
    """match uuid in canonical book list"""
    if len(containing_books) == 0:
        raise Exception(
            "No containing books.\n"
            f"content: {module_uuid}\n"
            f"module link: {link}"
        )

    if len(containing_books) == 1:
        return containing_books[0]

    try:
        match = next(
            uuid for uuid in canonical_ids if uuid in containing_books
        )
    except StopIteration:
        raise Exception(
            "Multiple containing books, no canonical match!\n"
            f"content: {module_uuid}\n"
            f"module link: {link}\n"
            f"containing books: {containing_books}"
        )

    return match


@timed
def patch_link(node, legacy_id, module_uuid, match, page_slug):
    """replace legacy link"""
    print('BEFORE:')
    print(node.attrib)
    original_href = node.attrib["href"]
    # Link may have fragment
    if "#" in original_href:
        page_fragment = f"#{original_href.split('#')[1]}"
    else:
        page_fragment = ""
    uuid = module_uuid.split('@')[0]
    node.attrib["href"] = f"./{match}:{uuid}.xhtml{page_fragment}"
    node.attrib["data-book-uuid"] = match
    node.attrib["data-page-slug"] = page_slug
    print('AFTER:')
    print(node.attrib)


@timed
def save_linked_collection(output_dir, doc):
    """write modified output"""
    linked_collection = f"{output_dir}/collection.linked.xhtml"
    with open(f"{linked_collection}", "wb") as f:
        doc.write(f, encoding="utf-8", xml_declaration=True)


@timed
def transform_links(data_dir, server, canonical_list, adapter):
    # define the canonical books
    canonical_ids = load_canonical_list(canonical_list)

    doc = load_assembled_collection(data_dir)

    session = init_requests_session(adapter)

    page_slug_resolver = gen_page_slug_resolver(session, server)

    # look up uuids for external module links
    for node in doc.xpath(
            '//x:a[@href and starts-with(@href, "/contents/m")]',
            namespaces={"x": "http://www.w3.org/1999/xhtml"},
    ):

        link = node.attrib["href"]
        legacy_id = find_legacy_id(link)

        module_uuid = get_target_uuid(session, server, legacy_id)
        containing_books = get_containing_books(session, server, module_uuid)

        match = match_canonical_book(
            canonical_ids,
            containing_books,
            module_uuid,
            link
        )

        page_slug = page_slug_resolver(match, module_uuid)
        if page_slug is None:
            raise Exception(
                f"Could not find page slug for module {legacy_id} "
                f"in canonical book UUID {match}"
            )
        patch_link(node, legacy_id, module_uuid, match, page_slug)

    save_linked_collection(data_dir, doc)


@timed
def main():  # pragma: no cover
    data_dir, server, canonical_list = sys.argv[1:4]
    adapter = requests.adapters.HTTPAdapter(max_retries=MAX_RETRIES)
    transform_links(data_dir, server, canonical_list, adapter)


if __name__ == "__main__":  # pragma: no cover
    main()
