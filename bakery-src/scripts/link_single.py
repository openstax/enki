"""
Replaces legacy module ids in links to external modules with
uuids from the target module and corresponding canonical book       .
"""

import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote

from .html_parser import reconstitute
from .cnx_models import flatten_to_documents, flatten_model, CompositeDocument
from lxml import etree
from .profiler import timed
from .utils import build_rex_url


@timed
def load_baked_collection(input_dir, book_slug):
    """load assembled collection"""
    baked_collection = f"{input_dir}/{book_slug}.baked.xhtml"
    return etree.parse(baked_collection)


@timed
def parse_collection_binders(input_dir):
    """Create a list of binders from book collections"""
    baked_collections = Path(input_dir).glob("*.baked.xhtml")
    binders = []

    for baked_collection in baked_collections:
        with open(baked_collection, "r") as baked_file:
            binder = reconstitute(baked_file)
            binders.append(binder)

    return binders


@timed
def create_canonical_map(binders):
    """Create a canonical book map from a set of binders"""
    canonical_map = {}

    for binder in binders:
        for doc in flatten_to_documents(binder):
            canonical_map[doc.id] = doc.metadata['canonical_book_uuid']

    return canonical_map


@timed
def parse_book_metadata(binders, input_dir):
    """Create a list of book metadata for a set of binders using collection
    metadata files"""
    book_metadata = []

    for binder in binders:
        slug = binder.metadata["slug"]
        baked_metadata_file = Path(input_dir) / f"{slug}.baked-metadata.json"
        with open(baked_metadata_file, "r") as metadata_file:
            metadata = json.load(metadata_file)
            book_metadata.append(metadata[binder.ident_hash])

    return book_metadata


@timed
def get_target_uuid(link):
    """get target module uuid"""
    parsed = unquote(link)

    return re.search(
        r'/contents/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})',
        parsed).group(1)


@timed
def gen_page_slug_resolver(book_tree_by_uuid):
    """Generate a page slug resolver function"""

    def _get_page_slug(book_uuid, page_uuid):
        """Get page slug from book"""

        def _parse_tree_for_slug(tree, page_uuid):
            """Recursively walk through tree to find page slug"""
            curr_slug = tree["slug"]
            curr_id = tree["id"]
            if curr_id.startswith(page_uuid):
                return curr_slug
            if "contents" in tree:
                for node in tree["contents"]:
                    slug = _parse_tree_for_slug(node, page_uuid)
                    if slug:
                        return slug
            return None

        page_slug = _parse_tree_for_slug(
            book_tree_by_uuid[book_uuid], page_uuid)

        return page_slug

    return _get_page_slug


@timed
def gen_composite_page_slug_resolver(binders_by_book_uuid, page_slug_resolver):
    """Generate a composite page slug resolver function"""

    parsed_by_id = {}

    def _get_composite_page_uuid(book_uuid, composite_page_id):
        """Get composite page uuid from binder"""

        binder = binders_by_book_uuid.get(book_uuid)
        if binder:
            encoded_page_id = composite_page_id.encode("utf-8")
            for model in flatten_model(binder):
                if not isinstance(model, CompositeDocument):
                    continue

                model_id, content = model.id, model.content
                if encoded_page_id in content:
                    parsed = parsed_by_id.setdefault(
                        model_id, etree.fromstring(content)
                    )
                    id_search = parsed.xpath(
                        './/*[@data-type="composite-page"]/@id'
                    )
                    if id_search and id_search[0] == composite_page_id:
                        return model_id

        return None

    def _get_composite_page_slug(book_uuid, composite_page_id):
        composite_page_uuid = _get_composite_page_uuid(
            book_uuid, composite_page_id
        )
        if not composite_page_uuid:
            return None
        return page_slug_resolver(book_uuid, composite_page_uuid)
    
    return _get_composite_page_slug


@timed
def patch_link(node, source_book_uuid, canonical_book_uuid,
               canonical_book_slug, page_slug, version):
    """replace legacy link"""
    # FIXME: Track and change EXTERNAL #id-based links in link-extras that have moved from baking
    # m12345 -> uuid::abcd
    # /content/m12345/index.xhtml#exercise -> /content/uuid::abcd/index.xhtml#exercise,
    # but if #exercise has moved, then it should be /content/uuid::other/index.xhtml#exercise
    # This can be fixed via searching the baked content when encountering link with a #.... suffix

    if not source_book_uuid == canonical_book_uuid:
        page_link = node.attrib["href"].split("/contents/")[1]
        # Link may have fragment
        if "#" in page_link:
            page_id, page_fragment = page_link.split('#')
            page_fragment = f"#{page_fragment}"
        else:
            page_id = page_link
            page_fragment = ""

        node.attrib["data-book-uuid"] = canonical_book_uuid
        node.attrib["data-book-slug"] = canonical_book_slug
        node.attrib["data-page-slug"] = page_slug
        node.attrib["href"] = f"./{canonical_book_uuid}@{version}:{page_id}.xhtml{page_fragment}"


@timed
def save_linked_collection(output_path, doc):
    """write modified output"""
    with open(output_path, "wb") as f:
        doc.write(f, encoding="utf-8", xml_declaration=True)


@timed
def transform_rex_links(
    doc, slug_by_uuid, page_slug_resolver, composite_page_slug_resolver
):
    """
    Transform Rex links in an XHTML document.

    Assumptions:
    - Each document contains exactly one book (canonical-book-uuid)
    - Page slugs stored by page id
    - Composite page slugs stored by generated title sequence id
    - Composite page ids are unique within a single book

    """
    # TODO: If the plan to remove metadata elements ever happens, this query
    # would probably become '//x:body/@canonical-book-uuid'
    # Alternatively, we could get the book id from canonical_map using the
    # first page's id. Then we don't need to query directly, but that approach
    # may be less readable
    book_uuid_search = doc.xpath(
        '//*[@data-type="canonical-book-uuid"]/@data-value'
    )
    assert book_uuid_search, 'Could no find book uuid'
    book_uuid = book_uuid_search[0]
    book_slug = slug_by_uuid.get(book_uuid)
    assert book_slug, f'Could not find slug for book: {book_uuid}'
    for node in doc.xpath(
        '//x:a[@data-needs-rex-link="true"]',
        namespaces={'x': 'http://www.w3.org/1999/xhtml'},
    ):
        try:
            parent_page_search = node.xpath(
                'ancestor::*[@data-type="page" or @data-type="composite-page"]'
            )
            assert parent_page_search, 'Could not find parent page'
            parent_page = parent_page_search[0]
            data_type = parent_page.attrib['data-type']
            page_id = parent_page.attrib['id']
            page_id = page_id[5:] if page_id.startswith('page_') else page_id
            if data_type == 'page':
                page_slug = page_slug_resolver(book_uuid, page_id)
            else:
                page_slug = composite_page_slug_resolver(book_uuid, page_id)
            assert page_slug, f'Could not find slug for page: {page_id}'
            node.attrib['href'] = build_rex_url(book_slug, page_slug)
        except Exception as e:
            # If we cannot formulate the link, try to link directly to the
            # element's src
            # The assumption is the the href's parent also contains the iframe
            # the href is meant to link to
            parent_link = node.xpath('parent::*//*[@src]/@src')
            assert parent_link, \
                f'Could not find link for element: {etree.tostring(node)}'
            node.attrib['href'] = parent_link[0]
            print(f"[WARNING]: {e} (used '{parent_link}' instead)")
        finally:
            del node.attrib['data-needs-rex-link']

@timed
def transform_links(
        baked_content_dir, baked_meta_dir, source_book_slug, output_path, version, mock_otherbook):
    doc = load_baked_collection(baked_content_dir, source_book_slug)
    binders = parse_collection_binders(baked_content_dir)
    canonical_map = create_canonical_map(binders)
    book_metadata = parse_book_metadata(binders, baked_meta_dir)

    uuid_by_slug = {entry["slug"]: entry["id"] for entry in book_metadata}
    slug_by_uuid = dict(zip(*list(zip(*uuid_by_slug.items()))[::-1]))
    book_tree_by_uuid = {
        entry["id"]: entry["tree"] for entry in book_metadata
    }
    source_book_uuid = uuid_by_slug[source_book_slug]
    page_slug_resolver = gen_page_slug_resolver(
        book_tree_by_uuid
    )
    binders_by_book_uuid = {binder.id: binder for binder in binders}
    composite_page_slug_resolver = gen_composite_page_slug_resolver(
        binders_by_book_uuid, page_slug_resolver,
    )

    transform_rex_links(
        doc, slug_by_uuid, page_slug_resolver, composite_page_slug_resolver
    )

    # look up uuids for external module links
    for node in doc.xpath(
            '//x:a[@href and starts-with(@href, "/contents/")]',
            namespaces={"x": "http://www.w3.org/1999/xhtml"},
    ):
        link = node.attrib["href"]

        target_module_uuid = get_target_uuid(link)
        canonical_book_uuid = canonical_map.get(target_module_uuid)

        if ((not canonical_book_uuid == source_book_uuid) and mock_otherbook):
            # If the canonical book UUID doesn't equal the current book (which
            # includes if the lookup returned None) and we're mocking otherbook
            # links, go ahead and insert the mock.
            node.attrib["href"] = "mock-inter-book-link"
            node.attrib["data-book-uuid"] = "mock-inter-book-uuid"
            continue
        elif (canonical_book_uuid is None):
            raise Exception(
                f"Could not find canonical book for {target_module_uuid}"
            )
        canonical_book_slug = slug_by_uuid[canonical_book_uuid]

        page_slug = page_slug_resolver(canonical_book_uuid, target_module_uuid)
        if page_slug is None:
            raise Exception(
                f"Could not find page slug for module {target_module_uuid} "
                f"in canonical book UUID {canonical_book_uuid} "
                f"from link {link}"
            )  # pragma: no cover
        patch_link(node, source_book_uuid, canonical_book_uuid,
                   canonical_book_slug, page_slug, version)

    save_linked_collection(output_path, doc)


@timed
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("baked_content_dir")
    parser.add_argument("baked_meta_dir")
    parser.add_argument("source_book_slug")
    parser.add_argument("output_path")
    parser.add_argument("version")
    parser.add_argument("--mock-otherbook", action="store_true")
    args = parser.parse_args()

    transform_links(
        args.baked_content_dir,
        args.baked_meta_dir,
        args.source_book_slug,
        args.output_path,
        args.version,
        args.mock_otherbook
    )


if __name__ == "__main__":  # pragma: no cover
    main()
