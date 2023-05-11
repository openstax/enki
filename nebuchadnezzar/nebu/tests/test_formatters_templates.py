import pytest
from nebu.formatters import _doc_to_html, _col_to_html, assemble_collection


@pytest.fixture
def current_snapshot_dir(snapshot_dir):
    return snapshot_dir / "raw"


# Raw means no exercises, no id updates, unresolved links
def test_doc_to_html(assert_match, parts_tuple):
    _, docs_by_id, _ = parts_tuple

    for doc_id, document in docs_by_id.items():
        assert_match(_doc_to_html(document), doc_id + ".xhtml")


def test_col_to_html(assert_match, parts_tuple):
    from nebu.models.book_part import PartType

    collection, _, _ = parts_tuple
    assert_match(_col_to_html(collection), "collection.xhtml")
    for i, subcol in enumerate(collection.get_parts_by_type(PartType.SUBCOL)):
        assert_match(_col_to_html(subcol), f"subcol-{i}.xhtml")


def test_assemble_collection(assert_match, parts_tuple):
    from lxml import etree

    collection, _, _ = parts_tuple
    assembled_collection = assemble_collection(collection)
    assert_match(
        etree.tostring(
            assembled_collection, pretty_print=True, encoding="utf-8"
        ),
        "collection.assembled.xhtml",
    )
