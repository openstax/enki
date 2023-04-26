import json

import pytest
from nebu.models.book_part import BookPart
from nebu.xml_utils import etree_to_str


@pytest.fixture
def current_snapshot_dir(snapshot_dir):
    return snapshot_dir / "test_book_part"


def test_collection_from_file(assert_match, git_collection_data):
    collection, docs_by_id, docs_by_uuid = BookPart.collection_from_file(
        git_collection_data / "collection.xml"
    )

    def part_to_dict(book_part):
        return dict(
            type=book_part.type,
            metadata=book_part.metadata,
            children=[
                part_to_dict(child_part) for child_part in book_part.children
            ],
            content=(
                None
                if book_part.content is None
                else etree_to_str(book_part.content).decode()
            ),
        )

    collection_as_dict = part_to_dict(collection)
    assert_match(
        json.dumps(collection_as_dict, default=str, indent=2),
        "collection.json",
    )
    # Make sure that all the documents are accounted for in the uuid map
    assert all(
        doc.metadata["uuid"] in docs_by_uuid for doc in collection.documents
    )
    # Make sure that all the documents are accounted for in the id map
    assert all(
        doc.metadata["id"] in docs_by_id for doc in collection.documents
    )
