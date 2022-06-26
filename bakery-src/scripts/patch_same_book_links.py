"""Make modifications to page XHTML files specific to GDoc outputs
"""
import json
import sys
from pathlib import Path

from lxml import etree


def update_doc_links(doc, book_uuid, book_version):
    """Modify links in doc"""

    def _href_builder(page_uuid, fragment):
        fragment_part = f'#{fragment}' if fragment else ''
        href = f"./{book_uuid}@{book_version}:{page_uuid}.xhtml{fragment_part}"
        return href

    for node in doc.xpath(
            '//x:a[@href and starts-with(@href, "/contents/")]',
            namespaces={"x": "http://www.w3.org/1999/xhtml"}
    ):
        # This is either an intra-book link or inter-book link. We can
        # differentiate the latter by data-book-uuid attrib).
        if not node.attrib.get("data-book-uuid"):
            page_uuid = node.attrib["data-page-uuid"]
            page_fragment = node.attrib["data-page-fragment"]
            node.attrib["href"] = _href_builder(page_uuid, page_fragment)


def main():
    in_dir = Path(sys.argv[1]).resolve(strict=True)
    out_dir = Path(sys.argv[2]).resolve(strict=True)
    collection_prefix = sys.argv[3]

    xhtml_files = in_dir.glob("*@*.xhtml")
    book_metadata = in_dir / f"{collection_prefix}.toc-metadata.json"

    # Get the UUID of the book being processed
    with book_metadata.open() as json_file:
        json_data = json.load(json_file)
        book_uuid = json_data["id"]
        book_version = json_data["version"]

    for xhtml_file in xhtml_files:
        doc = etree.parse(str(xhtml_file))
        update_doc_links(
            doc,
            book_uuid,
            book_version
        )
        doc.write(str(out_dir / xhtml_file.name), encoding="utf8")


if __name__ == "__main__":  # pragma: no cover
    main()
