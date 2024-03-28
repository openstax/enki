from dataclasses import dataclass
import os
from uuid import uuid4

import pytest

import nebu.media_utils as media_utils


@pytest.fixture
def test_image(git_collection_data):
    @dataclass
    class TestImage:
        media_file: str
        filename: str
        sha1: str
        s3_md5: str
        width: int
        height: int
        mime_type: str

    image_file_name = "assemble-h5p-test-image.png"
    matches = list(git_collection_data.glob(f"**/{image_file_name}"))
    assert matches, f"Could not find image file: {image_file_name}"
    media_file = matches[0]
    return TestImage(
        str(media_file),
        os.path.basename(media_file),
        "94c1f9ecc18b5c530bb5311273c718bb1e5efeed",
        '"bc1136899a571daab39ca8e997ab3d5d"',
        64,
        64,
        "image/png"
    )


def test_get_checksums(test_image):
    sha1, s3_md5 = media_utils.get_checksums(test_image.media_file)
    assert sha1 == test_image.sha1
    assert s3_md5 == test_image.s3_md5


def test_get_size(test_image):
    width, height = media_utils.get_size(test_image.media_file)
    assert width == test_image.width
    assert height == test_image.height
    assert media_utils.get_size(str(uuid4())) == (-1, -1)


def test_get_mime_type(test_image):
    mime_type = media_utils.get_mime_type(test_image.media_file)
    assert mime_type == test_image.mime_type
    assert media_utils.get_mime_type(f"{uuid4()}.txt") == "text/plain"
    assert media_utils.get_mime_type(f"{uuid4()}.{uuid4()}") == ""


def test_get_media_metadata(test_image):
    expected_metadata = {
        "original_name": test_image.filename,
        "mime_type": test_image.mime_type,
        "s3_md5": test_image.s3_md5,
        "sha1": test_image.sha1,
        "width": test_image.width,
        "height": test_image.height,
    }
    sha1, metadata = media_utils.get_media_metadata(test_image.media_file, True)
    assert metadata == expected_metadata
    assert sha1 == test_image.sha1
