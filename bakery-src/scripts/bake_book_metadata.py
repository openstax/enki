import json
import sys

from cnxepub.collation import reconstitute
from cnxepub.html_parsers import DocumentMetadataParser
from lxml import etree

from . import utils


def main():
    raw_metadata_file, baked_xhtml_file, collection_uuid, book_slugs_file, baked_metadata_file = sys.argv[1:6]

    with open(baked_xhtml_file, "r") as baked_xhtml:
        html = etree.parse(baked_xhtml)
        metadata = DocumentMetadataParser(html)
        binder = reconstitute(baked_xhtml)

    with open(raw_metadata_file, "r") as raw_json:
        baked_metadata = json.load(raw_json)

    # Parse slug from JSON file if provided, else from the binder
    if book_slugs_file:
        with open(book_slugs_file, "r") as json_file:
            json_data = json.load(json_file)
            book_slugs_by_uuid = {
                elem["uuid"]: elem["slug"] for elem in json_data
            }
            book_slug = book_slugs_by_uuid[collection_uuid]
    else:
        book_slug = metadata.slug

    tree = utils.model_to_tree(binder)

    # Use any existing book metadata to determine whether to fallback to
    # values from the XHTML metadata
    book_metadata = baked_metadata.get(binder.ident_hash, {})

    baked_book_json = {
        "title": metadata.title,
        "revised": utils.ensure_isoformat(metadata.revised),
        "tree": tree,
        "slug": book_slug,
        "authors": metadata.authors,
        "type": metadata.type,
        "id": book_metadata.get("id") or binder.id,
        "version": book_metadata.get("version") or metadata.version,
        "license": book_metadata.get("license") or {
            "url": metadata.license_url,
            "name": metadata.license_text
        },
        "language": metadata.language
    }

    # If there is existing book metadata provided, update with data above
    if baked_metadata.get(binder.ident_hash):
        baked_metadata[binder.ident_hash].update(baked_book_json)
    else:
        baked_metadata[binder.ident_hash] = baked_book_json

    with open(baked_metadata_file, "w") as json_out:
        json.dump(
            baked_metadata,
            json_out
        )


if __name__ == "__main__":  # pragma: no cover
    main()
