import json
import sys
from pathlib import Path

from lxml import etree

from .utils import unformatted_rex_links
from .profiler import timed


@timed
def update_doc_links(doc, book_slugs_by_uuid=None):
    """Modify links in doc"""

    def _rex_url_builder(book, page):
        return f"http://openstax.org/books/{book}/pages/{page}"

    external_link_elems = unformatted_rex_links(doc)
    external_link_elems = unformatted_rex_links(doc)

    for node in external_link_elems:
        # This an inter-book link defined by data-book-uuid attrib
        if node.attrib.get("data-book-uuid"):
            print('BEFORE!!:')
            print(node.attrib)

            external_book_uuid = node.attrib["data-book-uuid"]
            external_book_slug = book_slugs_by_uuid[
                external_book_uuid] if book_slugs_by_uuid else node.attrib["data-book-slug"]
            external_page_slug = node.attrib["data-page-slug"]
            node.attrib["href"] = _rex_url_builder(
                external_book_slug, external_page_slug
            )
            print('AFTER!!:')
            print(node.attrib)


@timed
def main():
    """Main function"""
    xhtml_file = Path(sys.argv[1]).resolve(strict=True)
    out_dir = Path(sys.argv[3]).resolve(strict=True)
    filename = sys.argv[4]
    try:
        book_slugs_file = Path(sys.argv[2]).resolve(strict=True)
    except FileNotFoundError:
        book_slugs_file = None
        book_slugs_by_uuid = None

    if book_slugs_file:
        with book_slugs_file.open() as json_file:
            json_data = json.load(json_file)
            book_slugs_by_uuid = {
                elem["uuid"]: elem["slug"] for elem in json_data
            }

    doc = etree.parse(str(xhtml_file))
    update_doc_links(
        doc,
        book_slugs_by_uuid
    )
    doc.write(str(out_dir / filename), encoding="utf8")


if __name__ == "__main__":  # pragma: no cover
    main()
