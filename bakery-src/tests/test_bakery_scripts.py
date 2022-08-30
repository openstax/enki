"""Tests to validate JSON metadata extraction and file generation pipeline"""
import os
import json
from datetime import datetime
from enum import Enum
from glob import glob
from lxml import etree
import boto3
import botocore.stub
import requests_mock
import requests
import pytest
import re
from tempfile import TemporaryDirectory
from distutils.dir_util import copy_tree
from googleapiclient.discovery import build
import google.auth
from googleapiclient.http import RequestMockBuilder
from PIL import Image
from pathlib import Path
from filecmp import cmp

from cnxepub.html_parsers import HTML_DOCUMENT_NAMESPACES
from cnxepub.collation import reconstitute
from bakery_scripts import (
    jsonify_book,
    disassemble_book,
    link_extras,
    assemble_book_metadata,
    bake_book_metadata,
    check_feed,
    gdocify_book,
    mathmltable2png,
    copy_resources_s3,
    upload_docx,
    checksum_resource,
    fetch_map_resources,
    fetch_update_metadata,
    link_single,
    patch_same_book_links,
    link_rex,
    utils
)

HERE = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_DIR = os.path.join(HERE, "data")
TEST_JPEG_DIR = os.path.join(HERE, "test_jpeg_colorspace")
SCRIPT_DIR = os.path.join(HERE, "../scripts")


def test_link_rex_git(tmp_path, mocker):
    xhtml_file = "collection.mathified.xhtml"
    in_dir = tmp_path / "in"
    in_dir.mkdir()

    input_xhtml = os.path.join(TEST_DATA_DIR, xhtml_file)
    input_xhtml_file = in_dir / xhtml_file
    input_xhtml_file.write_bytes(open(input_xhtml, "rb").read())

    doc = etree.parse(str(input_xhtml_file))
    assert len(utils.unformatted_rex_links(doc)) > 0

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    filename = 'osbook.rex-linked.xhtml'

    mocker.patch("sys.argv", ["", input_xhtml_file,
                              "idontexistforGit", out_dir, filename])
    link_rex.main()

    outfile = os.path.join(out_dir, filename)
    updated_doc = etree.parse(str(outfile))
    assert len(utils.unformatted_rex_links(updated_doc)) == 0


def test_link_rex_archive(tmp_path, mocker):
    xhtml_file = "collection.mathified.xhtml"
    in_dir = tmp_path / "in"
    in_dir.mkdir()

    book_slugs = os.path.join(TEST_DATA_DIR, "book-slugs.json")
    book_slugs_file = in_dir / "book-slugs.json"
    book_slugs_file.write_bytes(open(book_slugs, "rb").read())

    input_xhtml = os.path.join(TEST_DATA_DIR, xhtml_file)
    input_xhtml_file = in_dir / xhtml_file
    input_xhtml_file.write_bytes(open(input_xhtml, "rb").read())

    doc = etree.parse(str(input_xhtml_file))
    assert len(utils.unformatted_rex_links(doc)) > 0

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    filename = 'osbook.rex-linked.xhtml'

    mocker.patch("sys.argv", ["", input_xhtml_file, book_slugs_file, out_dir, filename])
    link_rex.main()

    outfile = os.path.join(out_dir, filename)
    updated_doc = etree.parse(str(outfile))
    assert len(utils.unformatted_rex_links(updated_doc)) == 0


def test_checksum_resource(tmp_path, mocker):
    book_dir = tmp_path / "col00000"
    book_dir.mkdir()
    html_file = book_dir / "0.xhtml"
    module_dir = book_dir / "0"
    module_dir.mkdir()
    image_src = module_dir / "image_src.svg"
    image_href = module_dir / "image_href.svg"
    image_none = module_dir / "image_none.svg"

    # libmagic yields image/svg without the xml declaration
    image_src_content = ('<?xml version=1.0 ?>'
                         '<svg height="30" width="120">'
                         '<text x="0" y="15" fill="red">'
                         'checksum me!'
                         '</text>'
                         '</svg>')
    image_src_sha1_expected = "527617b308327b8773c5105edc8c28bcbbe62553"
    image_src_md5_expected = "420c64c8dbe981f216989328f9ad97e7"
    image_src.write_text(image_src_content)

    # libmagic yields image/svg without the xml declaration
    image_href_content = ('<?xml version=1.0 ?>'
                          '<svg height="30" width="120">'
                          '<text x="0" y="15" fill="red">'
                          'checksum me too!'
                          '</text>'
                          '</svg>')
    image_href_sha1_expected = "ad32bb3de1c805920a0ab50ab1333f39df8687a1"
    image_href_md5_expected = "46137319b2adb8b09c8f432343b8bcca"
    image_href.write_text(image_href_content)

    # libmagic yields image/svg without the xml declaration
    image_none_content = ('<?xml version=1.0 ?>'
                          '<svg height="30" width="120">'
                          '<text x="0" y="15" fill="red">'
                          'nope.'
                          '</text>'
                          '</svg>')
    image_none.write_text(image_none_content)

    html_content = ('<html xmlns="http://www.w3.org/1999/xhtml">'
                    '<img src="0/image_src.svg"/>'
                    '<a href="image_href.svg">linko</a>'
                    '</html>')
    html_file.write_text(html_content)

    mocker.patch(
        "sys.argv",
        ["", book_dir, book_dir]
    )
    checksum_resource.main()

    resource_dir = book_dir / "resources"
    image_src_meta = f"{image_src_sha1_expected}.json"
    image_href_meta = f"{image_href_sha1_expected}.json"
    assert set(path.name for path in resource_dir.glob("*")) == set([
        image_src_meta,
        image_href_meta,
        image_src_sha1_expected,
        image_href_sha1_expected
    ])
    assert json.load((resource_dir / image_src_meta).open("r")) == {
        'height': 30,
        'mime_type': 'image/svg+xml',
        'original_name': 'image_src.svg',
        # AWS needs the MD5 quoted inside the string json value.
        # Despite looking like a mistake, this is correct behavior.
        's3_md5': f'"{image_src_md5_expected}"',
        'sha1': image_src_sha1_expected,
        'width': 120
    }
    assert json.load((resource_dir / image_href_meta).open("r")) == {
        'height': 30,
        'mime_type': 'image/svg+xml',
        'original_name': 'image_href.svg',
        # AWS needs the MD5 quoted inside the string json value.
        # Despite looking like a mistake, this is correct behavior.
        's3_md5': f'"{image_href_md5_expected}"',
        'sha1': image_href_sha1_expected,
        'width': 120
    }
    assert resource_dir.exists()

    tree = etree.parse(str(html_file))
    expected = (f'<html xmlns="http://www.w3.org/1999/xhtml">'
                f'<img src="../resources/{image_src_sha1_expected}"/>'
                f'<a href="../resources/{image_href_sha1_expected}">linko</a>'
                f'</html>')
    assert etree.tostring(tree, encoding="utf8") == expected.encode("utf8")


def test_jsonify_book(tmp_path, mocker):
    """Test jsonify_book script"""

    html_content = "<html><body>test body</body></html>"
    toc_content = "<nav>TOC</nav>"
    json_metadata_content = {
        "title": "subsection title",
        "abstract": "subsection abstract",
        "slug": "1-3-subsection-slug",
    }

    mock_uuid = "00000000-0000-0000-0000-000000000000"
    mock_version = "0.0"
    mock_ident_hash = f"{mock_uuid}@{mock_version}"

    disassembled_input_dir = tmp_path / "disassembled"
    disassembled_input_dir.mkdir()

    xhtml_input = disassembled_input_dir / f"{mock_ident_hash}:m00001.xhtml"
    xhtml_input.write_text(html_content)
    toc_input = disassembled_input_dir / "collection.toc.xhtml"
    toc_input.write_text(toc_content)
    json_metadata_input = (
        disassembled_input_dir / f"{mock_ident_hash}:m00001-metadata.json"
    )
    json_metadata_input.write_text(json.dumps(json_metadata_content))

    jsonified_output_dir = tmp_path / "jsonified"
    jsonified_output_dir.mkdir()

    mocker.patch(
        "sys.argv", ["", disassembled_input_dir, tmp_path / "jsonified"]
    )
    jsonify_book.main()

    jsonified_output = jsonified_output_dir / f"{mock_ident_hash}:m00001.json"
    jsonified_output_data = json.loads(jsonified_output.read_text())
    jsonified_toc_output = jsonified_output_dir / "collection.toc.json"
    jsonified_toc_data = json.loads(jsonified_toc_output.read_text())

    assert jsonified_output_data.get("title") == json_metadata_content["title"]
    assert (
        jsonified_output_data.get("abstract")
        == json_metadata_content["abstract"]
    )
    assert jsonified_output_data.get("slug") == json_metadata_content["slug"]
    assert jsonified_output_data.get("content") == html_content
    assert jsonified_toc_data.get("content") == toc_content


def test_disassemble_book(tmp_path, mocker):
    """Test disassemble_book script"""
    input_baked_xhtml = os.path.join(TEST_DATA_DIR, "collection.baked.xhtml")
    input_baked_metadata = os.path.join(
        TEST_DATA_DIR, "collection.baked-metadata.json"
    )

    input_dir = tmp_path / "book"
    input_dir.mkdir()

    input_baked_xhtml_file = input_dir / "collection.baked.xhtml"
    input_baked_xhtml_file.write_bytes(open(input_baked_xhtml, "rb").read())
    input_baked_metadata_file = input_dir / "collection.baked-metadata.json"
    input_baked_metadata_file.write_text(
        open(input_baked_metadata, "r").read()
    )

    disassembled_output = input_dir / "disassembled"
    disassembled_output.mkdir()

    mock_uuid = "00000000-0000-0000-0000-000000000000"
    mock_version = "0.0"
    mock_ident_hash = f"{mock_uuid}@{mock_version}"

    mocker.patch("sys.argv", ["",
                              str(input_baked_xhtml_file),
                              str(input_baked_metadata_file),
                              "collection",
                              str(disassembled_output)])
    disassemble_book.main()

    xhtml_output_files = glob(f"{disassembled_output}/*.xhtml")
    assert len(xhtml_output_files) == 3
    json_output_files = glob(f"{disassembled_output}/*-metadata.json")
    assert len(json_output_files) == 3

    # Check for expected files and metadata that should be generated in
    # this step
    json_output_m42119 = (
        disassembled_output / f"{mock_ident_hash}:m42119-metadata.json"
    )
    json_output_m42092 = (
        disassembled_output / f"{mock_ident_hash}:m42092-metadata.json"
    )
    m42119_data = json.load(open(json_output_m42119, "r"))
    m42092_data = json.load(open(json_output_m42092, "r"))
    assert (
        m42119_data.get("title")
        == "Introduction to Science and the Realm of Physics, "
        "Physical Quantities, and Units"
    )
    assert (
        m42119_data.get("slug")
        == "1-introduction-to-science-and-the-realm-of-physics-physical-"
        "quantities-and-units"
    )
    assert m42119_data["abstract"] is None
    assert m42119_data["revised"] == "2018/08/03 15:49:52 -0500"
    assert m42092_data.get("title") == "Physics: An Introduction"
    assert m42092_data.get("slug") == "1-1-physics-an-introduction"
    assert (
        m42092_data.get("abstract")
        == "Explain the difference between a model and a theory"
    )
    assert m42092_data["revised"] is not None
    # Verify the generated timestamp is ISO8601 and includes timezone info
    assert datetime.fromisoformat(m42092_data["revised"]).tzinfo is not None

    toc_output = disassembled_output / "collection.toc.xhtml"
    assert toc_output.exists()
    toc_output_tree = etree.parse(open(toc_output))
    nav = toc_output_tree.xpath(
        "//xhtml:nav", namespaces=HTML_DOCUMENT_NAMESPACES
    )
    assert len(nav) == 1
    toc_metadata_output = disassembled_output / "collection.toc-metadata.json"
    assert toc_metadata_output.exists()
    toc_metadata = json.load(open(toc_metadata_output, "r"))
    assert toc_metadata.get("title") == "College Physics"

    # Ensure same-book-links have additional metadata
    m42119_tree = etree.parse(
        open(disassembled_output / "00000000-0000-0000-0000-000000000000@0.0:m42119.xhtml")
    )
    link = m42119_tree.xpath(
        "//xhtml:a[@href='/contents/m42092#58161']", namespaces=HTML_DOCUMENT_NAMESPACES
    )[0]
    link.attrib["data-page-slug"] = "1-1-physics-an-introduction"
    link.attrib["data-page-uuid"] = "m42119"
    assert link.attrib["data-page-fragment"] == "58161"


def test_disassemble_book_empty_baked_metadata(tmp_path, mocker):
    """Test case for disassemble where there may not be associated metadata
    from previous steps in collection.baked-metadata.json
    """
    input_baked_xhtml = os.path.join(TEST_DATA_DIR, "collection.baked.xhtml")

    input_dir = tmp_path / "book"
    input_dir.mkdir()

    input_baked_xhtml_file = input_dir / "collection.baked.xhtml"
    input_baked_xhtml_file.write_bytes(open(input_baked_xhtml, "rb").read())
    input_baked_metadata_file = input_dir / "collection.baked-metadata.json"
    input_baked_metadata_file.write_text(json.dumps({}))

    disassembled_output = input_dir / "disassembled"
    disassembled_output.mkdir()

    mock_uuid = "00000000-0000-0000-0000-000000000000"
    mock_version = "0.0"
    mock_ident_hash = f"{mock_uuid}@{mock_version}"

    mocker.patch("sys.argv", ["",
                              str(input_baked_xhtml_file),
                              str(input_baked_metadata_file),
                              "collection",
                              str(disassembled_output)])
    disassemble_book.main()

    # Check for expected files and metadata that should be generated in this
    # step
    json_output_m42119 = (
        disassembled_output / f"{mock_ident_hash}:m42119-metadata.json"
    )
    json_output_m42092 = (
        disassembled_output / f"{mock_ident_hash}:m42092-metadata.json"
    )
    m42119_data = json.load(open(json_output_m42119, "r"))
    m42092_data = json.load(open(json_output_m42092, "r"))
    assert m42119_data["abstract"] is None
    assert m42119_data["id"] == "m42119"
    assert m42092_data["abstract"] is None
    assert m42092_data["id"] == "m42092"


def test_canonical_list_order():
    """Test if legacy ordering of canonical books is preserved"""
    canonical_list = os.path.join(SCRIPT_DIR, "canonical-book-list.json")

    with open(canonical_list) as canonical:
        books = json.load(canonical)
        names = [book["_name"] for book in books["canonical_books"]]

    assert {"College Algebra", "Precalculus"}.issubset(set(names))
    assert names.index("College Algebra") < names.index("Precalculus")

    # All 1e books should come after 2e variants
    assert names.index("American Government 2e") < \
        names.index("American Government 1e")
    assert names.index("Biology 2e") < names.index("Biology 1e")
    assert names.index("Chemistry 2e") < names.index("Chemistry 1e")
    assert names.index("Chemistry 2e") < \
        names.index("Chemistry: Atoms First 1e")
    assert names.index("Biology 2e") < \
        names.index("Concepts of Biology")
    assert names.index("Introduction to Sociology 2e") < \
        names.index("Introduction to Sociology 1e")
    assert names.index("Principles of Economics 2e") < \
        names.index("Principles of Economics 1e")
    assert names.index("Principles of Economics 2e") < \
        names.index("Principles of Macroeconomics 1e")
    assert names.index("Principles of Economics 2e") < \
        names.index("Principles of Macroeconomics for AP Courses 1e")
    assert names.index("Principles of Economics 2e") < \
        names.index("Principles of Microeconomics 1e")
    assert names.index("Principles of Economics 2e") < \
        names.index("Principles of Microeconomics for AP Courses 1e")

    # Check for expected ordering within 1e variants
    assert names.index("Biology 1e") < names.index("Concepts of Biology")
    assert names.index("Chemistry 1e") < \
        names.index("Chemistry: Atoms First 1e")
    assert names.index("Principles of Economics 1e") < \
        names.index("Principles of Macroeconomics 1e")
    assert names.index("Principles of Macroeconomics 1e") < \
        names.index("Principles of Microeconomics 1e")
    assert names.index("Principles of Microeconomics 1e") < \
        names.index("Principles of Macroeconomics for AP Courses 1e")
    assert names.index("Principles of Macroeconomics for AP Courses 1e") < \
        names.index("Principles of Microeconomics for AP Courses 1e")


def mock_link_extras(tmp_path, content_dict, contents_dict, extras_dict,
                     page_content):
    input_dir = tmp_path / "linked-extras"
    input_dir.mkdir()

    server = "mock.archive"

    canonical_list = f"{SCRIPT_DIR}/canonical-book-list.json"

    adapter = requests_mock.Adapter()

    content_matcher = re.compile(f"https://{server}/content/")

    def content_callback(request, context):
        module_uuid = content_dict[request.url.split("/")[-1]]
        context.status_code = 301
        context.headers['Location'] = \
            f"https://{server}/contents/{module_uuid}"
        return

    adapter.register_uri("GET", content_matcher, json=content_callback)

    extras_matcher = re.compile(f"https://{server}/extras/")

    def extras_callback(request, context):
        return extras_dict[request.url.split("/")[-1]]

    adapter.register_uri("GET", extras_matcher, json=extras_callback)

    contents_matcher = re.compile(f"https://{server}/contents/")

    def contents_callback(request, context):
        return contents_dict[request.url.split("/")[-1]]

    adapter.register_uri("GET", contents_matcher, json=contents_callback)

    collection_name = "collection.assembled.xhtml"
    collection_input = input_dir / collection_name
    collection_input.write_text(page_content)

    link_extras.transform_links(input_dir, server, canonical_list, adapter)


def test_link_extras_single_match(tmp_path, mocker):
    """Test for link_extras script case with single
    containing book and a canonical match"""

    content_dict = {"m12345": "1234-5678-1234-5678@version"}

    contents_dict = {
        "00000000-0000-0000-0000-000000000000": {
            "tree": {
                "id": "",
                "slug": "",
                "contents": [
                    {
                        "id": "1234-5678-1234-5678@version",
                        "slug": "1234-slug"
                    }
                ]
            }
        }
    }

    extras_dict = {
        "1234-5678-1234-5678@version": {
            "books": [{"ident_hash": "00000000-0000-0000-0000-000000000000@1"}]
        }
    }

    page_content = """
        <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
        <div data-type="page">
        <p><a id="l1"
            href="/contents/internal-uuid"
            class="target-chapter">Intra-book module link</a></p>
        <p><a id="l2"
            href="/contents/m12345"
            class="target-chapter"
            data-book-uuid="otheruuid">Inter-book module link</a></p>
        <p><a id="l3"
            href="#foobar"
            class="autogenerated-content">Reference in page</a></p>
        <p><a id="l4" href="http://www.openstax.org/l/shorturl">
            External shortened link</a></p>
        <p><a id="l5"
            href="/contents/m12345#fragment"
            class="target-chapter"
            data-book-uuid="otheruuid">Inter-book link with fragment</a></p>
        </div>
        </body>
        </html>
    """

    expected_links = [
        [
            ("id", "l1"),
            ("href", "/contents/internal-uuid"),
            ("class", "target-chapter"),
        ],
        [
            ("id", "l2"),
            ("href", "./00000000-0000-0000-0000-000000000000:1234-5678-1234-5678.xhtml"),
            ("class", "target-chapter"),
            ("data-book-uuid", "00000000-0000-0000-0000-000000000000"),
            ("data-page-slug", "1234-slug"),
        ],
        [
            ("id", "l5"),
            ("href", "./00000000-0000-0000-0000-000000000000:1234-5678-1234-5678.xhtml#fragment"),
            ("class", "target-chapter"),
            ("data-book-uuid", "00000000-0000-0000-0000-000000000000"),
            ("data-page-slug", "1234-slug"),
        ],
    ]

    mock_link_extras(tmp_path, content_dict, contents_dict, extras_dict,
                     page_content)

    output_dir = tmp_path / "linked-extras"

    collection_output = output_dir / "collection.linked.xhtml"
    tree = etree.parse(str(collection_output))

    parsed_links = tree.xpath(
        '//x:a[@href and starts-with(@href, "/contents/") or starts-with(@href, "./")]',
        namespaces={"x": "http://www.w3.org/1999/xhtml"},
    )

    check_links = [
        link.items() for link in parsed_links
    ]

    assert check_links == expected_links


def test_link_extras_no_containing(tmp_path, mocker):
    """Test for link_extras script case with no
    containing books"""

    content_dict = {"m12345": "1234-5678-1234-5678@version"}

    contents_dict = {}

    extras_dict = {
        "1234-5678-1234-5678@version": {
            "books": []
        }
    }

    page_content = """
        <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
        <div data-type="page">
        <p><a id="l1"
            href="/contents/internal-uuid"
            class="target-chapter">Intra-book module link</a></p>
        <p><a id="l2"
            href="/contents/m12345"
            class="target-chapter"
            data-book-uuid="otheruuid">Inter-book module link</a></p>
        <p><a id="l3"
            href="#foobar"
            class="autogenerated-content">Reference in page</a></p>
        <p><a id="l4" href="http://www.openstax.org/l/shorturl">
            External shortened link</a></p>
        </div>
        </body>
        </html>
    """

    with pytest.raises(
        Exception,
        match=r'(No containing books).*\n(content).*\n(module link)'
    ):
        mock_link_extras(tmp_path, content_dict, contents_dict, extras_dict,
                         page_content)


def test_link_extras_single_no_match(tmp_path, mocker):
    """Test for link_extras script case with single
    containing book and no canonical match"""

    content_dict = {"m12345": "1234-5678-1234-5678@version"}

    contents_dict = {
        "4664c267-cd62-4a99-8b28-1cb9b3aee347": {
            "tree": {
                "id": "",
                "slug": "",
                "contents": [
                    {
                        "id": "1234-5678-1234-5678@version",
                        "slug": "1234-slug"
                    }
                ]
            }
        }
    }

    extras_dict = {
        "1234-5678-1234-5678@version": {
            "books": [{"ident_hash": "4664c267-cd62-4a99-8b28-1cb9b3aee347@1"}]
        }
    }

    page_content = """
        <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
        <div data-type="page">
        <p><a id="l1"
            href="/contents/internal-uuid"
            class="target-chapter">Intra-book module link</a></p>
        <p><a id="l2"
            href="/contents/m12345"
            class="target-chapter"
            data-book-uuid="otheruuid">Inter-book module link</a></p>
        <p><a id="l3"
            href="#foobar"
            class="autogenerated-content">Reference in page</a></p>
        <p><a id="l4" href="http://www.openstax.org/l/shorturl">
            External shortened link</a></p>
        </div>
        </body>
        </html>
    """

    expected_links = [
        [
            ("id", "l1"),
            ("href", "/contents/internal-uuid"),
            ("class", "target-chapter"),
        ],
        [
            ("id", "l2"),
            ("href", "./4664c267-cd62-4a99-8b28-1cb9b3aee347:1234-5678-1234-5678.xhtml"),
            ("class", "target-chapter"),
            ("data-book-uuid", "4664c267-cd62-4a99-8b28-1cb9b3aee347"),
            ("data-page-slug", "1234-slug"),
        ],
    ]

    mock_link_extras(tmp_path, content_dict, contents_dict, extras_dict,
                     page_content)

    output_dir = tmp_path / "linked-extras"

    collection_output = output_dir / "collection.linked.xhtml"
    tree = etree.parse(str(collection_output))

    parsed_links = tree.xpath(
        '//x:a[@href and starts-with(@href, "/contents/") or starts-with(@href, "./")]',
        namespaces={"x": "http://www.w3.org/1999/xhtml"},
    )

    check_links = [
        link.items() for link in parsed_links
    ]

    assert check_links == expected_links


def test_link_extras_multi_match(tmp_path, mocker):
    """Test for link_extras script case with multiple
    containing book and a canonical match"""

    content_dict = {"m12345": "1234-5678-1234-5678@version"}

    contents_dict = {
        "4664c267-cd62-4a99-8b28-1cb9b3aee347": {
            "tree": {
                "id": "",
                "slug": "",
                "contents": [
                    {
                        "id": "1234-5678-1234-5678@version",
                        "slug": "1234-slug"
                    }
                ]
            }
        }
    }

    extras_dict = {
        "1234-5678-1234-5678@version": {
            "books": [
                {"ident_hash": "00000000-0000-0000-0000-000000000000@1"},
                {"ident_hash": "4664c267-cd62-4a99-8b28-1cb9b3aee347@1"},
            ]
        }
    }

    page_content = """
        <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
        <div data-type="page">
        <p><a id="l1"
            href="/contents/internal-uuid"
            class="target-chapter">Intra-book module link</a></p>
        <p><a id="l2"
            href="/contents/m12345"
            class="target-chapter"
            data-book-uuid="otheruuid">Inter-book module link</a></p>
        <p><a id="l3"
            href="#foobar"
            class="autogenerated-content">Reference in page</a></p>
        <p><a id="l4" href="http://www.openstax.org/l/shorturl">
            External shortened link</a></p>
        </div>
        </body>
        </html>
    """

    expected_links = [
        [
            ("id", "l1"),
            ("href", "/contents/internal-uuid"),
            ("class", "target-chapter"),
        ],
        [
            ("id", "l2"),
            ("href", "./4664c267-cd62-4a99-8b28-1cb9b3aee347:1234-5678-1234-5678.xhtml"),
            ("class", "target-chapter"),
            ("data-book-uuid", "4664c267-cd62-4a99-8b28-1cb9b3aee347"),
            ("data-page-slug", "1234-slug"),
        ],
    ]

    mock_link_extras(tmp_path, content_dict, contents_dict, extras_dict,
                     page_content)

    output_dir = tmp_path / "linked-extras"

    collection_output = output_dir / "collection.linked.xhtml"
    tree = etree.parse(str(collection_output))

    parsed_links = tree.xpath(
        '//x:a[@href and starts-with(@href, "/contents/") or starts-with(@href, "./")]',
        namespaces={"x": "http://www.w3.org/1999/xhtml"},
    )

    check_links = [
        link.items() for link in parsed_links
    ]

    assert check_links == expected_links


def test_link_extras_multi_no_match(tmp_path, mocker):
    """Test for link_extras script case with multiple
    containing book and a canonical match"""

    content_dict = {"m12345": "1234-5678-1234-5678@version"}

    contents_dict = {}

    extras_dict = {
        "1234-5678-1234-5678@version": {
            "books": [
                {"ident_hash": "00000000-0000-0000-0000-000000000000@1"},
                {"ident_hash": "11111111-1111-1111-1111-111111111111@1"},
            ]
        }
    }

    page_content = """
        <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
        <div data-type="page">
        <p><a id="l1"
            href="/contents/internal-uuid"
            class="target-chapter">Intra-book module link</a></p>
        <p><a id="l2"
            href="/contents/m12345"
            class="target-chapter"
            data-book-uuid="otheruuid">Inter-book module link</a></p>
        <p><a id="l3"
            href="#foobar"
            class="autogenerated-content">Reference in page</a></p>
        <p><a id="l4" href="http://www.openstax.org/l/shorturl">
            External shortened link</a></p>
        </div>
        </body>
        </html>
    """

    with pytest.raises(
        Exception,
        match=r'(no canonical).*\n.*(content).*\n.*(link).*\n.*(containing)'
    ):
        mock_link_extras(tmp_path, content_dict, contents_dict, extras_dict,
                         page_content)


def test_link_extras_page_slug_not_found(tmp_path):
    """Test for exception if page slug is not found"""
    content_dict = {"m12345": "1234-5678-1234-5678@version"}

    contents_dict = {
        "00000000-0000-0000-0000-000000000000": {
            "tree": {
                "id": "",
                "slug": "",
                "contents": [
                    {
                        "id": "",
                        "slug": ""
                    }
                ]
            }
        }
    }

    extras_dict = {
        "1234-5678-1234-5678@version": {
            "books": [{"ident_hash": "00000000-0000-0000-0000-000000000000@1"}]
        }
    }

    page_content = """
        <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
        <div data-type="page">
        <p><a id="l1"
            href="/contents/m12345"
            class="target-chapter"
            data-book-uuid="otheruuid">Inter-book module link</a></p>
        </div>
        </body>
        </html>
    """

    with pytest.raises(
        Exception,
        match=r'(Could not find page slug for module)'
    ):
        mock_link_extras(tmp_path, content_dict, contents_dict, extras_dict,
                         page_content)


def test_link_extras_page_slug_resolver(requests_mock):
    """Test page slug resolver in link_extras script"""
    requests_mock.get(
        "/contents/4664c267-cd62-4a99-8b28-1cb9b3aee347",
        json={
            "tree": {
                "id": "",
                "slug": "",
                "contents": [
                    {
                        "id": "1234-5678-1234-5678@version",
                        "slug": "1234-slug"
                    },
                    {
                        "id": "1111-2222-3333-4444@version",
                        "slug": "1111-slug"
                    }
                ]
            }
        }
    )

    page_slug_resolver = link_extras.gen_page_slug_resolver(
        requests.Session(),
        "mock.archive"
    )

    res = page_slug_resolver(
        "4664c267-cd62-4a99-8b28-1cb9b3aee347",
        "1234-5678-1234-5678@version"
    )
    assert res == "1234-slug"
    assert requests_mock.call_count == 1
    # Query slug for different page in same book to ensure the mocker isn't
    # called again
    requests_mock.reset_mock()
    res = page_slug_resolver(
        "4664c267-cd62-4a99-8b28-1cb9b3aee347",
        "1111-2222-3333-4444@version"
    )
    assert res == "1111-slug"
    assert requests_mock.call_count == 0

    # Test for unmatched slug
    res = page_slug_resolver(
        "4664c267-cd62-4a99-8b28-1cb9b3aee347",
        "foobar@version"
    )
    assert res is None


def test_assemble_book_metadata(tmp_path, mocker):
    """Test assemble_book_metadata script"""
    input_assembled_book = os.path.join(TEST_DATA_DIR,
                                        "assembled-book",
                                        "collection.assembled.xhtml")

    input_uuid_to_revised = tmp_path / "uuid-to-revised-map.json"
    with open(input_uuid_to_revised, 'w') as f:
        json.dump({
            "m42119": "2018/08/03 15:49:52 -0500",
            "m42092": "2018/09/18 09:55:13.413 GMT-5"
        }, f)

    assembled_metadata_output = tmp_path / "collection.assembed-metadata.json"

    mocker.patch(
        "sys.argv", ["", input_assembled_book, input_uuid_to_revised, assembled_metadata_output]
    )
    assemble_book_metadata.main()

    assembled_metadata = json.loads(assembled_metadata_output.read_text())
    assert assembled_metadata["m42119@1.6"]["abstract"] is None
    assert (
        "Explain the difference between a model and a theory"
        in assembled_metadata["m42092@1.10"]["abstract"]
    )
    assert (
        assembled_metadata["m42092@1.10"]["revised"]
        == "2018-09-18T09:55:13.413000-05:00"
    )
    assert (
        assembled_metadata["m42119@1.6"]["revised"]
        == "2018-08-03T15:49:52-05:00"
    )


def test_assemble_book_metadata_empty_revised_json(tmp_path, mocker):
    """Test assemble_book_metadata script when the revised JSON is empty
    to confirm it will fallback to metadata in assembled file
    """
    input_assembled_book = os.path.join(TEST_DATA_DIR,
                                        "assembled-book",
                                        "collection.assembled.xhtml")

    input_uuid_to_revised = tmp_path / "uuid-to-revised-map.json"
    input_uuid_to_revised.write_text(json.dumps({}))

    assembled_metadata_output = tmp_path / "collection.assembed-metadata.json"

    mocker.patch(
        "sys.argv", ["", input_assembled_book, input_uuid_to_revised, assembled_metadata_output]
    )
    assemble_book_metadata.main()

    assembled_metadata = json.loads(assembled_metadata_output.read_text())
    assert (
        assembled_metadata["m42092@1.10"]["revised"]
        == "2018-09-18T09:55:13.413000-05:00"
    )
    assert (
        assembled_metadata["m42119@1.6"]["revised"]
        == "2018-08-03T15:49:52-05:00"
    )


def test_bake_book_metadata(tmp_path, mocker):
    """Test bake_book_metadata script"""
    input_raw_metadata = os.path.join(
        TEST_DATA_DIR, "collection.assembled-metadata.json"
    )
    input_baked_xhtml = os.path.join(TEST_DATA_DIR, "collection.baked.xhtml")
    output_baked_book_metadata = tmp_path / "collection.toc-metadata.json"
    book_uuid = "031da8d3-b525-429c-80cf-6c8ed997733a"
    book_slugs = [
        {
            "uuid": book_uuid,
            "slug": "test-book-slug"
        }
    ]
    book_slugs_input = tmp_path / "book-slugs.json"
    book_slugs_input.write_text(json.dumps(book_slugs))

    with open(input_baked_xhtml, "r") as baked_xhtml:
        binder = reconstitute(baked_xhtml)
        book_ident_hash = binder.ident_hash

    mocker.patch(
        "sys.argv",
        [
            "",
            input_raw_metadata,
            input_baked_xhtml,
            book_uuid,
            book_slugs_input,
            output_baked_book_metadata,
        ],
    )
    bake_book_metadata.main()

    baked_metadata = json.loads(output_baked_book_metadata.read_text())
    book_metadata = baked_metadata[book_ident_hash]

    assert isinstance(book_metadata["tree"], dict) is True
    assert "contents" in book_metadata["tree"].keys()
    assert "license" in book_metadata.keys()
    assert (
        book_metadata["revised"]
        == "2021-02-26T10:51:35.574000-06:00"
    )
    assert "College Physics" in book_metadata["title"]
    assert book_metadata["slug"] == "test-book-slug"
    assert book_metadata["id"] == "injected_id"
    assert book_metadata["version"] == "injected_version"
    assert book_metadata["legacy_id"] == "injected_legacy_id"
    assert book_metadata["legacy_version"] == "injected_legacy_version"
    assert book_metadata["language"] == "en"


def test_bake_book_metadata_git(tmp_path, mocker):
    """Test bake_book_metadata script with git storage inputs"""
    input_baked_xhtml = os.path.join(
        TEST_DATA_DIR, "collection.baked-single.xhtml"
    )
    input_raw_metadata = tmp_path / "collection.assembled-metadata.json"
    output_baked_book_metadata = tmp_path / "collection.toc-metadata.json"

    input_raw_metadata.write_text(json.dumps({}))

    with open(input_baked_xhtml, "r") as baked_xhtml:
        binder = reconstitute(baked_xhtml)
        book_ident_hash = binder.ident_hash

    mocker.patch(
        "sys.argv",
        [
            "",
            input_raw_metadata,
            input_baked_xhtml,
            "",
            "",
            output_baked_book_metadata,
        ],
    )
    bake_book_metadata.main()

    baked_metadata = json.loads(output_baked_book_metadata.read_text())
    book_metadata = baked_metadata[book_ident_hash]

    assert isinstance(book_metadata["tree"], dict) is True
    assert "contents" in book_metadata["tree"].keys()
    assert "license" in book_metadata.keys()
    assert (
        book_metadata["revised"]
        == "2019-08-30T16:35:37.569966-05:00"
    )
    assert "College Physics" in book_metadata["title"]
    assert book_metadata["slug"] == "physics"
    assert book_metadata["id"] == "c7795d04-cfca-4ec6-a30f-f48d06336635"
    assert book_metadata["version"] == "1.2.3"
    assert book_metadata["language"] == "en"


def test_check_feed(tmp_path, mocker):
    """Test check_feed script"""
    input_book_feed = {
        "approved_books": [
            {
                "collection_id": "col11762",
                "style": "sociology",
                "server": "cnx.foobar.org",
                "tutor_only": False,
                "books": [
                    {
                        "uuid": "02040312-72c8-441e-a685-20e9333f3e1d",
                        "slug": "introduction-sociology-2e"
                    }
                ]
            },
            {
                "collection_id": "col11406",
                "style": "college-physics",
                "server": "cnx.foobar.org",
                "tutor_only": False,
                "books": [
                    {
                        "uuid": "031da8d3-b525-429c-80cf-6c8ed997733a",
                        "slug": "college-physics"
                    }
                ]
            },
            {
                "repository_name": "osbooks-writing-guide",
                "platforms": ["rex"],
                "versions": [{
                    "repository_name": "osbooks-writing-guide",
                    "min_code_version": "1.42",
                    "edition": 1,
                    "commit_sha": "4ff250a4779bc500660063acb85b7aab7df94396",
                    "commit_metadata": {
                        "committed_at": "2021-10-25T10:47:06+00:00",
                        "books": [{
                            "uuid": "ee7ce46b-0972-4b2c-bc6e-8998c785cd57",
                            "style": "english-composition",
                            "slug": "writing-guide"
                        }]
                    }
                }]
            },
        ],
        "approved_versions": [
            {
                "collection_id": "col11762",
                "content_version": "1.14.1",
                "min_code_version": "20210101.00000000"
            },
            {
                # This version should be ignored due to code version
                "collection_id": "col11762",
                "content_version": "1.14.2",
                "min_code_version": "20210101.00000002"
            },
            {
                "collection_id": "col11406",
                "content_version": "1.20.15",
                "min_code_version": "20210101.00000001"
            },
            {
                "repository_name": "osbooks-college-algebra-bundle",
                "content_version": "1",
                "min_code_version": "20210101.00000001"
            }
        ]
    }

    json_feed_input = tmp_path / "book-feed.json"
    json_feed_input.write_text(json.dumps(input_book_feed))

    # We'll use the botocore stubber to play out a simple scenario to test the
    # script where we'll trigger multiple invocations to "build" all books
    # above. Documenting this in words just to help with readability and
    # maintainability.
    #
    # Expected s3 requests / responses by invocation:
    #
    # Invocation 1 (archive):
    #   - book 1
    #       - Initial check for .complete: head_object => Return a 404
    #       - Check for .pending: head_object => Return a 404
    #       - put_object by script with book data
    #       - put_object by script with .pending state

    # Invocation 2 (archive):
    #   - book 1 (emulate a failure from first invocation)
    #       - Check for .complete => head_object => Return a 404
    #       - Check for .pending: head_object => Return data
    #       - Check for .retry: head_object => Return 404
    #       - put_object by script with book data
    #       - put_object by script with .retry state
    #
    # Invocation 3 (archive):
    #   - book 1
    #       - Check for .complete => head_object return object
    #   - book 2
    #       - Initial check for .complete: head_object => Return a 404
    #       - Check for .pending head_object => Return a 404
    #       - put_object by script with book data
    #       - put_object by script with .pending state
    #
    # Invocation 4 (git):
    #   - book 3
    #       - Initial check for .complete: head_object => Return a 404
    #       - Check for .pending head_object => Return a 404
    #       - put_object by script with book data
    #       - put_object by script with .pending state
    #
    # Invocation 5 (git):
    #   - book 3
    #       - Check for .complete => head_object return object
    #   - book 4
    #       - Initial check for .complete: head_object => Return a 404
    #       - Check for .pending head_object => Return a 404
    #       - put_object by script with book data
    #       - put_object by script with .pending state

    queue_state_bucket = "queue-state-bucket"
    queue_filename = "queue-state-filename.json"
    code_version = "20210101.00000001"
    state_prefix = "foobar"
    book1 = {
        "collection_id": "col11762",
        "server": "cnx.foobar.org",
        "style": "sociology",
        "uuid": "02040312-72c8-441e-a685-20e9333f3e1d",
        "slug": "introduction-sociology-2e",
        "version": "1.14.1"
    }
    book1_col = book1["collection_id"]
    book1_vers = book1["version"]
    book2 = {
        "collection_id": "col11406",
        "server": "cnx.foobar.org",
        "style": "college-physics",
        "uuid": "031da8d3-b525-429c-80cf-6c8ed997733a",
        "slug": "college-physics",
        "version": "1.20.15"
    }
    book2_col = book2["collection_id"]
    book2_vers = book2["version"]

    s3_client = boto3.client("s3")
    s3_stubber = botocore.stub.Stubber(s3_client)

    def _stubber_add_head_object_404(expected_key):
        s3_stubber.add_client_error(
            "head_object",
            service_error_meta={"Code": "404"},
            expected_params={
                "Bucket": queue_state_bucket,
                "Key": expected_key,
            },
        )

    def _stubber_add_head_object(expected_key):
        s3_stubber.add_response(
            "head_object",
            {},
            expected_params={
                "Bucket": queue_state_bucket,
                "Key": expected_key,
            },
        )

    def _stubber_add_put_object(expected_key, expected_body):
        s3_stubber.add_response(
            "put_object",
            {},
            expected_params={
                "Bucket": queue_state_bucket,
                "Key": expected_key,
                "Body": expected_body,
            },
        )

    # Add expected calls for archive books

    # Book 1: Check for .complete file
    _stubber_add_head_object_404(
        f"{code_version}/.{state_prefix}.{book1_col}@{book1_vers}.complete"
    )

    # Book 1: Check for .pending file
    _stubber_add_head_object_404(
        f"{code_version}/.{state_prefix}.{book1_col}@{book1_vers}.pending"
    )

    # Book 1: Put book data
    _stubber_add_put_object(queue_filename, json.dumps(book1))

    # Book 1: Put book .pending
    _stubber_add_put_object(
        f"{code_version}/.{state_prefix}.{book1_col}@{book1_vers}.pending",
        botocore.stub.ANY
    )

    # Book 1: Check for .complete file
    _stubber_add_head_object_404(
        f"{code_version}/.{state_prefix}.{book1_col}@{book1_vers}.complete"
    )

    # Book 1: Check for .pending file (return as though it exists)
    _stubber_add_head_object(
        f"{code_version}/.{state_prefix}.{book1_col}@{book1_vers}.pending"
    )

    # Book 1: Check for .retry file
    _stubber_add_head_object_404(
        f"{code_version}/.{state_prefix}.{book1_col}@{book1_vers}.retry"
    )

    # Book 1: Put book data again
    _stubber_add_put_object(queue_filename, json.dumps(book1))

    # Book 1: Put book .retry
    _stubber_add_put_object(
        f"{code_version}/.{state_prefix}.{book1_col}@{book1_vers}.retry",
        botocore.stub.ANY
    )

    # Book 1: Check for .complete file
    _stubber_add_head_object(
        f"{code_version}/.{state_prefix}.{book1_col}@{book1_vers}.complete"
    )

    # Book 2: Check for .complete file
    _stubber_add_head_object_404(
        f"{code_version}/.{state_prefix}.{book2_col}@{book2_vers}.complete"
    )

    # Book 2: Check for .pending file
    _stubber_add_head_object_404(
        f"{code_version}/.{state_prefix}.{book2_col}@{book2_vers}.pending"
    )

    # Book 2: Put book data
    _stubber_add_put_object(queue_filename, json.dumps(book2))

    # Book 2: Put book .pending
    _stubber_add_put_object(
        f"{code_version}/.{state_prefix}.{book2_col}@{book2_vers}.pending",
        botocore.stub.ANY
    )

    s3_stubber.activate()

    mocker.patch("boto3.client", lambda service: s3_client)
    mocker.patch(
        "sys.argv",
        [
            "",
            json_feed_input,
            code_version,
            queue_state_bucket,
            queue_filename,
            1,
            state_prefix,
            "archive"
        ],
    )

    for _ in range(3):
        check_feed.main()

    s3_stubber.assert_no_pending_responses()

    # Add expected calls for git books

    book3 = {
        "repo": "osbooks-writing-guide",
        "version": "4ff250a4779bc500660063acb85b7aab7df94396"
    }

    book3_slug = book3["repo"]
    book3_vers = book3["version"]

    # Book 3: Check for .complete file
    _stubber_add_head_object_404(
        f"{code_version}/.{state_prefix}.{book3_slug}@{book3_vers}.complete"
    )

    # Book 3: Check for .pending file
    _stubber_add_head_object_404(
        f"{code_version}/.{state_prefix}.{book3_slug}@{book3_vers}.pending"
    )

    # Book 3: Put book data
    _stubber_add_put_object(queue_filename, json.dumps(book3))

    # Book 3: Put book .pending
    _stubber_add_put_object(
        f"{code_version}/.{state_prefix}.{book3_slug}@{book3_vers}.pending",
        botocore.stub.ANY
    )

    # Book 3: Check for .complete file
    _stubber_add_head_object(
        f"{code_version}/.{state_prefix}.{book3_slug}@{book3_vers}.complete"
    )

    mocker.patch(
        "sys.argv",
        [
            "",
            json_feed_input,
            code_version,
            queue_state_bucket,
            queue_filename,
            1,
            state_prefix,
            "git"
        ],
    )

    for _ in range(2):
        check_feed.main()

    s3_stubber.assert_no_pending_responses()

    mocker.patch(
        "sys.argv",
        [
            "",
            json_feed_input,
            code_version,
            queue_state_bucket,
            queue_filename,
            1,
            state_prefix,
            "invalidfilter"
        ],
    )

    with pytest.raises(Exception, match='Invalid feed filter value'):
        check_feed.main()

    s3_stubber.assert_no_pending_responses()
    s3_stubber.deactivate()


def test_patch_same_book_links(tmp_path, mocker):
    """Test patch_same_book_links script"""
    input_dir = tmp_path / "disassembled"
    input_dir.mkdir()
    output_dir = tmp_path / "internal-linked"
    output_dir.mkdir()

    book_metadata = {
        "id": "bookuuid1",
        "version": "version"
    }

    page_content = """
        <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
        <div data-type="page">
        <p><a id="l1"
            href="/contents/internal-uuid"
            data-page-uuid="internal-uuid"
            data-page-slug="l1-page-slug"
            data-page-fragment=""
            class="target-chapter">Intra-book module link</a></p>
        <p><a id="l2"
            href="./otheruuid:external-uuid"
            class="target-chapter"
            data-book-uuid="otheruuid"
            data-page-slug="l2-page-slug">Inter-book module link</a></p>
        <p><a id="l3"
            href="#foobar"
            class="autogenerated-content">Reference in page</a></p>
        <p><a id="l4" href="http://www.openstax.org/l/shorturl">
            External shortened link</a></p>
        <p><a id="l5"
            href="/contents/internal-uuid#foobar"
            data-page-uuid="internal-uuid"
            data-page-slug="l1-page-slug"
            data-page-fragment="foobar"
            class="target-chapter">Intra-book module link with fragment</a></p>
        </div>
        </body>
        </html>
    """

    toc_input = input_dir / "collection.toc.xhtml"
    toc_input.write_text("DUMMY")
    book_metadata_input = input_dir / "collection.toc-metadata.json"
    book_metadata_input.write_text(json.dumps(book_metadata))
    page_name = "bookuuid1@version:pageuuid1.xhtml"
    page_input = input_dir / page_name
    page_input.write_text(page_content)

    mocker.patch("sys.argv", ["", input_dir, output_dir, "collection"])
    patch_same_book_links.main()

    page_output = output_dir / page_name
    assert page_output.exists()

    expected_links_by_id = {
        "l1": "./bookuuid1@version:internal-uuid.xhtml",
        "l2": "./otheruuid:external-uuid",
        "l3": "#foobar",
        "l4": "http://www.openstax.org/l/shorturl",
        "l5": "./bookuuid1@version:internal-uuid.xhtml#foobar",
    }

    updated_doc = etree.parse(str(page_output))

    for node in updated_doc.xpath(
        "//x:a[@href]", namespaces={"x": "http://www.w3.org/1999/xhtml"},
    ):
        assert expected_links_by_id[node.attrib["id"]] == node.attrib["href"]


@pytest.mark.asyncio
async def test_gdocify_book(tmp_path, mocker):
    """Test gdocify_book script"""

    input_dir = tmp_path / "disassembled"
    input_dir.mkdir()
    output_dir = tmp_path / "gdocified"
    output_dir.mkdir()

    page_content = """
        <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
        <div data-type="page">
        <p><a id="l1"
            href="/contents/internal-uuid"
            data-page-uuid="internal-uuid"
            data-page-slug="l1-page-slug"
            data-page-fragment=""
            class="target-chapter">Intra-book module link</a></p>
        <p><a id="l2"
            href="./otheruuid:external-uuid"
            class="target-chapter"
            data-book-uuid="otheruuid"
            data-page-slug="l2-page-slug">Inter-book module link</a></p>
        <p><a id="l3"
            href="#foobar"
            class="autogenerated-content">Reference in page</a></p>
        <p><a id="l4" href="http://www.openstax.org/l/shorturl">
            External shortened link</a></p>
        <p><a id="l5"
            href="/contents/internal-uuid#foobar"
            data-page-uuid="internal-uuid"
            data-page-slug="l1-page-slug"
            data-page-fragment="foobar"
            class="target-chapter">Intra-book module link with fragment</a></p>
        <p><iframe src="http://www.example.com/"></iframe></p>
        <math>
            <mrow>
                <mtext mathvariant="bold-italic">x</mtext>
            </mrow>
        </math>
        <math>
            <semantics>
                <mrow>
                    <mrow>
                        <mrow>
                            <msubsup>
                                <mrow>
                                    <mi>N</mi>
                                    <mo>′</mo>
                                </mrow>
                                <mrow>
                                    <mtext>R</mtext>
                                </mrow>
                            </msubsup>
                        </mrow>
                        <mrow></mrow>
                    </mrow>
                </mrow>
                <annotation-xml encoding="MathML-Content">
                    <semantics>
                        <mrow>
                            <mrow>
                                <msubsup>
                                    <mrow>
                                        <mi>N</mi>
                                        <mo>′</mo>
                                    </mrow>
                                    <mrow>
                                        <mtext>R</mtext>
                                    </mrow>
                                </msubsup>
                            </mrow>
                            <mrow></mrow>
                        </mrow>
                        <annotation encoding="StarMath 5.0"> size 12{ { {N}} sup { x } rSub { size 8{R} } } {}</annotation>
                    </semantics>
                </annotation-xml>
            </semantics>
        </math>
        <math>
            <semantics>
                <mi>N</mi>
                <annotation encoding="StarMath 5.0">{N}</annotation>
            </semantics>
        </math>
        <math>
            <semantics>
                <mrow>
                    <mo>–</mo>
                    <mi>N</mi>
                </mrow>
                <mrow>
                    <mo>–∞</mo>
                </mrow>
                <mrow>
                    <mo>–identifier</mo>
                </mrow>
                <mrow>
                    <mo>-20</mo>
                </mrow>
                <mrow>
                    <mo>cos</mo>
                </mrow>
                <mrow>
                    <mo>20</mo>
                </mrow>
                <mrow>
                    <mo>&#x201c;UNICODE QUOTES&#x201d;</mo>
                </mrow>
                <mrow>
                    <mo>Not an operator</mo>
                </mrow>
                <mrow>
                    <mo> </mo>
                </mrow>
                <mrow>
                    <mo>&#x00a0;</mo>
                </mrow>
                <mrow>
                    <mn>4̸</mn>
                </mrow>
            </semantics>
        </math>
        </div>
        </body>
        </html>
    """  # noqa: E501

    l1_page_metadata = {
        "slug": "l1-page-slug"
    }

    book_slugs = [
        {
            "uuid": "bookuuid1",
            "slug": "bookuuid1-slug"
        },
        {
            "uuid": "otheruuid",
            "slug": "otheruuid-slug"
        }
    ]

    # Populate a dummy TOC to confirm it is ignored
    toc_input = input_dir / "collection.toc.xhtml"
    toc_input.write_text("DUMMY")
    page_name = "bookuuid1@version:pageuuid1.xhtml"
    page_input = input_dir / page_name
    page_input.write_text(page_content)
    l1_page_metadata_name = "bookuuid1@version:internal-uuid-metadata.json"
    l1_page_metadata_input = input_dir / l1_page_metadata_name
    book_slugs_input = tmp_path / "book-slugs.json"
    book_slugs_input.write_text(json.dumps(book_slugs))
    worker_count = 1

    l1_page_metadata_input.write_text(json.dumps(l1_page_metadata))

    # Test complete script
    mocker.patch("sys.argv", ["", input_dir, output_dir, book_slugs_input, worker_count])
    await gdocify_book.run_async()

    page_output = output_dir / page_name
    assert page_output.exists()

    expected_links_by_id = {
        "l1": "http://openstax.org/books/bookuuid1-slug/pages/l1-page-slug",
        "l2": "http://openstax.org/books/otheruuid-slug/pages/l2-page-slug",
        "l3": "#foobar",
        "l4": "http://www.openstax.org/l/shorturl",
        "l5": "http://openstax.org/books/bookuuid1-slug/"
              "pages/l1-page-slug#foobar",
    }

    updated_doc = etree.parse(str(page_output))

    for node in updated_doc.xpath(
        "//x:a[@href]", namespaces={"x": "http://www.w3.org/1999/xhtml"},
    ):
        assert expected_links_by_id[node.attrib["id"]] == node.attrib["href"]

    for node in updated_doc.xpath(
        '//x:*[@mathvariant="bold-italic"]',
        namespaces={"x": "http://www.w3.org/1999/xhtml"},
    ):
        assert "mi" == node.tag.split("}")[1]

    # Was mo converted to mi in this case?
    assert(
        "mi" == updated_doc.xpath(
            '//*[text() = "–identifier"]',
            namespaces={"x": "http://www.w3.org/1999/xhtml"},
        )[0].tag.split("}")[1]
    )

    # Was mo converted to mn in this case?
    assert(
        "mn" == updated_doc.xpath(
            '//*[text() = "-20"]',
            namespaces={"x": "http://www.w3.org/1999/xhtml"},
        )[0].tag.split("}")[1]
    )

    # Was mo converted to mtext in this case?
    assert(
        "mtext" == updated_doc.xpath(
            '//*[text() = "“UNICODE QUOTES”"]',  # Not an error
            namespaces={"x": "http://www.w3.org/1999/xhtml"},
        )[0].tag.split("}")[1]
    )

    # Were mo's containing whitespace converted to mtext?
    assert(
        "mtext" == updated_doc.xpath(
            '//*[text() = " "]',
            namespaces={"x": "http://www.w3.org/1999/xhtml"},
        )[0].tag.split("}")[1]
    )

    assert(
        "mtext" == updated_doc.xpath(
            '//*[text() = "\xa0"]',
            namespaces={"x": "http://www.w3.org/1999/xhtml"},
        )[0].tag.split("}")[1]
    )

    # Do all mo tags contain only whitelisted characters?
    for node in updated_doc.xpath(
        '//x:mo',
        namespaces={"x": "http://www.w3.org/1999/xhtml"},
    ):
        if node.text is not None:
            text_len = len(node.text)
            assert text_len > 0
            if text_len == 1:
                assert node.text in gdocify_book.CHARLISTS['mo_single']
            else:
                assert node.text in gdocify_book.CHARLISTS['mo_multi']

    # Are all mi tags free of blacklisted characters?
    for node in updated_doc.xpath(
        '//x:mi',
        namespaces={"x": "http://www.w3.org/1999/xhtml"},
    ):
        if node.text is not None:
            assert not any(char in node.text
                           for char in gdocify_book.CHARLISTS["mi_blacklist"])

    unwanted_nodes = updated_doc.xpath(
        '//x:annotation-xml',
        namespaces={"x": "http://www.w3.org/1999/xhtml"},
    )
    assert len(unwanted_nodes) == 0

    unwanted_nodes = updated_doc.xpath(
        '//x:annotation',
        namespaces={"x": "http://www.w3.org/1999/xhtml"},
    )
    assert len(unwanted_nodes) == 0

    unwanted_nodes = updated_doc.xpath(
        '//x:msubsup[count(*) < 3]',
        namespaces={"x": "http://www.w3.org/1999/xhtml"},
    )
    assert len(unwanted_nodes) == 0

    unwanted_nodes = updated_doc.xpath(
        '//x:msub[count(*) > 2]',
        namespaces={"x": "http://www.w3.org/1999/xhtml"},
    )
    assert len(unwanted_nodes) == 0

    msub_nodes = updated_doc.xpath(
        '//x:msub',
        namespaces={"x": "http://www.w3.org/1999/xhtml"},
    )
    assert len(msub_nodes) == 1

    unwanted_nodes = updated_doc.xpath(
        '//x:iframe',
        namespaces={"x": "http://www.w3.org/1999/xhtml"},
    )
    assert len(unwanted_nodes) == 0

    unwanted_nodes = updated_doc.xpath(
        f'//x:mi[contains(text(), "\u0338")]|//x:mn[contains(text(), "\u0338")]',
        namespaces={"x": "http://www.w3.org/1999/xhtml"},
    )
    assert len(unwanted_nodes) == 0

    # Test fix_jpeg_colorspace

    # use a simplified RESOURCES_FOLDER path for testing
    mocker.patch('bakery_scripts.gdocify_book.RESOURCES_FOLDER', './')
    mocker.patch('bakery_scripts.gdocify_book.USWEBCOATEDSWOP_ICC',
                 '/usr/share/color/icc/ghostscript/default_cmyk.icc')

    def resolve_img_path(img_filename, out_dir):
        return (out_dir / img_filename).resolve().absolute()

    with TemporaryDirectory() as temp_dir:
        # copy test JPEGs into a temporal dir
        copy_tree(TEST_JPEG_DIR, temp_dir)

        rf = './'
        rgb = rf + 'rgb.jpg'
        rgb_broken = rf + 'rgb_broken.jpg'
        cmyk = rf + 'cmyk.jpg'
        cmyk_no_profile = rf + 'cmyk_no_profile.jpg'
        cmyk_broken = rf + 'cmyk_broken.jpg'
        greyscale = rf + 'greyscale.jpg'
        greyscale_broken = rf + 'greyscale_broken.jpg'
        png = rf + 'original_public_domain.png'

        old_dir = os.getcwd()
        os.chdir(temp_dir)

        # convert to RGB
        await gdocify_book.fix_jpeg_colorspace(
            resolve_img_path(cmyk, Path(temp_dir)))

        im = Image.open(os.path.join(temp_dir, cmyk))
        assert im.mode == 'RGB'
        im.close()

        copy_tree(TEST_JPEG_DIR, temp_dir)  # reset test case
        im = Image.open(os.path.join(temp_dir, cmyk))
        assert im.mode == 'CMYK'
        im.close()
        im = Image.open(os.path.join(temp_dir, cmyk_no_profile))
        assert im.mode == 'CMYK'
        im.close()

        # convert no profile fully to RGB
        await gdocify_book.fix_jpeg_colorspace(
            resolve_img_path(cmyk_no_profile, Path(temp_dir)))

        im = Image.open(os.path.join(temp_dir, cmyk))
        assert im.mode == 'CMYK'
        im.close()
        im = Image.open(os.path.join(temp_dir, cmyk_no_profile))
        assert im.mode == 'RGB'
        im.close()

        copy_tree(TEST_JPEG_DIR, temp_dir)  # reset test case
        im = Image.open(os.path.join(temp_dir, cmyk))
        assert im.mode == 'CMYK'
        im.close()
        im = Image.open(os.path.join(temp_dir, cmyk_no_profile))
        assert im.mode == 'CMYK'
        im.close()

        # keep sure only CMYK is converted
        xhtml = """
            <html xmlns="http://www.w3.org/1999/xhtml">
            <body>
                <img src="{0}" />
                <img src="{0}" />
                <img src="{1}" />
                <a href="{3}">hallo</a>
                <img src="{2}" />
                <img src="{1}" />
                <a href="{1}">hallo2</a>
                <a href="{4}">hallo3</a>
            </body>
            </html>
        """.format(rgb, greyscale, png, cmyk, cmyk_no_profile)
        doc = etree.fromstring(xhtml)
        async with gdocify_book.AsyncJobQueue(worker_count) as queue:
            for img_filename in gdocify_book.get_img_resources(doc, Path(temp_dir)):
                queue.put_nowait(gdocify_book.fix_jpeg_colorspace(img_filename))

        assert cmp(os.path.join(TEST_JPEG_DIR, rgb),
                   os.path.join(temp_dir, rgb))
        assert cmp(os.path.join(TEST_JPEG_DIR, greyscale),
                   os.path.join(temp_dir, greyscale))
        assert cmp(os.path.join(TEST_JPEG_DIR, png),
                   os.path.join(temp_dir, png))

        im = Image.open(os.path.join(temp_dir, cmyk))
        assert im.mode == 'RGB'
        im.close()

        im = Image.open(os.path.join(temp_dir, cmyk_no_profile))
        assert im.mode == 'RGB'
        im.close()

        # convert non existing
        # this is a corner case which should not happen in the pipeline
        with pytest.raises(Exception, match=r'^Error\: Resource file not existing\:.*'):
            await gdocify_book.fix_jpeg_colorspace(
                resolve_img_path('./idontexist.jpg', Path(temp_dir)))

        copy_tree(TEST_JPEG_DIR, temp_dir)  # reset test case
        im = Image.open(os.path.join(temp_dir, cmyk))
        assert im.mode == 'CMYK'
        im.close()
        im = Image.open(os.path.join(temp_dir, cmyk_no_profile))
        assert im.mode == 'CMYK'
        im.close()

        # don't fix invalid images
        xhtml = """
            <html xmlns="http://www.w3.org/1999/xhtml">
            <body>
                <img src="{0}" />
                <a href="{0}" />
                <img src="{1}" />
                <img src="{2}" />
                <img src="{4}" />
                <img src="{3}" />
                <img src="{4}" />
            </body>
            </html>
        """.format(rgb_broken, greyscale_broken, cmyk, cmyk_broken, png)
        doc = etree.fromstring(xhtml)
        # should only give warnings but should not break
        async with gdocify_book.AsyncJobQueue(worker_count) as queue:
            for img_filename in gdocify_book.get_img_resources(doc, Path(temp_dir)):
                queue.put_nowait(gdocify_book.fix_jpeg_colorspace(img_filename))

        im = Image.open(os.path.join(temp_dir, cmyk))
        assert im.mode == 'RGB'
        im.close()

        assert cmp(os.path.join(TEST_JPEG_DIR, cmyk_broken),
                   os.path.join(temp_dir, cmyk_broken))
        assert cmp(os.path.join(TEST_JPEG_DIR, rgb_broken),
                   os.path.join(temp_dir, rgb_broken))
        assert cmp(os.path.join(TEST_JPEG_DIR, greyscale_broken),
                   os.path.join(temp_dir, greyscale_broken))
        assert cmp(os.path.join(TEST_JPEG_DIR, png),
                   os.path.join(temp_dir, png))

        copy_tree(TEST_JPEG_DIR, temp_dir)  # reset test case
        im = Image.open(os.path.join(temp_dir, cmyk))
        assert im.mode == 'CMYK'
        im.close()

        mocker.patch("bakery_scripts.gdocify_book._convert_cmyk2rgb_embedded_profile",
                     return_value="mogrify -invalid")
        with pytest.raises(Exception, match=r'^Error converting file.*'):
            await gdocify_book.fix_jpeg_colorspace(
                resolve_img_path(cmyk, Path(temp_dir)))

        os.chdir(old_dir)


def test_mathmltable2png(tmp_path, mocker):
    """Test python parts of mathmltable2png"""

    # ==================================
    # test mathjax svg invalid xml patch
    # ==================================

    invalid_svg_parts = '''<svg><g data-semantic-operator="<"/></svg>'''
    supposed_patched_svg_parts = '''<svg><g data-semantic-operator="&lt;"/></svg>'''
    patched_svg_parts = mathmltable2png.patch_mathjax_svg_invalid_xml(invalid_svg_parts)
    assert patched_svg_parts == supposed_patched_svg_parts

    # real world svg parts
    invalid_svg_parts = '''<svg>
    <g data-semantic-operator="relseq,<" data-mml-node="mo" data-semantic-type="relation" data-semantic-role="inequality" data-semantic-id="9" data-semantic-parent="19" transform="translate(3260.3, 0)" />
    </svg>'''  # noqa: E501
    supposed_patched_svg_parts = '''<svg>
    <g data-semantic-operator="relseq,&lt;" data-mml-node="mo" data-semantic-type="relation" data-semantic-role="inequality" data-semantic-id="9" data-semantic-parent="19" transform="translate(3260.3, 0)" />
    </svg>'''  # noqa: E501
    patched_svg_parts = mathmltable2png.patch_mathjax_svg_invalid_xml(invalid_svg_parts)
    assert patched_svg_parts == supposed_patched_svg_parts

    # does not happen in real world but test the regEx patching anyway with multiple lines
    invalid_svg_parts = '''<svg>
    <g data-semantic-operator="<right" />
    <g data-semantic-operator="left<" />
    <g data-semantic-operator="in<between" />
    <g data-semantic-operator="donothingleft>" />
    <g data-semantic-operator=">donothingright" />
    <g data-semantic-operator="donothing>inbetween" />
    </svg>'''
    supposed_patched_svg_parts = '''<svg>
    <g data-semantic-operator="&lt;right" />
    <g data-semantic-operator="left&lt;" />
    <g data-semantic-operator="in&lt;between" />
    <g data-semantic-operator="donothingleft>" />
    <g data-semantic-operator=">donothingright" />
    <g data-semantic-operator="donothing>inbetween" />
    </svg>'''
    patched_svg_parts = mathmltable2png.patch_mathjax_svg_invalid_xml(invalid_svg_parts)
    assert patched_svg_parts == supposed_patched_svg_parts

    # Multiple operators should not happen to my knowledge. (therealmarv)
    # Test the breaking failure of the edge case within the edge case.
    invalid_svg_parts = '''<svg>
    <g data-semantic-operator="<<" />
    </svg>'''
    with pytest.raises(Exception, match=r'^Failed to generate valid XML out of SVG.*'):
        mathmltable2png.patch_mathjax_svg_invalid_xml(invalid_svg_parts)

    # Invalid unpatchable XML should also break the execution
    invalid_svg_parts = '<svg><HelloImNotValid></svg>'
    with pytest.raises(Exception, match=r'^Failed to generate valid XML out of SVG.*'):
        mathmltable2png.patch_mathjax_svg_invalid_xml(invalid_svg_parts)


# The ANY_VALUE and ANY_PARAM classes contain some shenanigans to allow us to use
# 2 different sets of expected params passed to the botocore stubber in any order
# Checking ANY_VALUE for equality constrains the valid param indexes in ANY_PARAM
class ANY_VALUE:
    def __init__(self, any_param, values):
        self.any_param = any_param
        self.values = values

    def __eq__(self, other):
        new_valid_param_indexes = []
        for value_index, param_index in enumerate(self.any_param.valid_param_indexes):
            if other == self.values[value_index]:
                new_valid_param_indexes.append(param_index)
        self.any_param.valid_param_indexes = new_valid_param_indexes
        return new_valid_param_indexes != []

    def __repr__(self):
        return f'<ANY OF {self.values}>'


class ANY_PARAM:
    # We want enums but don't want all the Enum class methods
    ABSENT = Enum('ANY_PARAM', 'ABSENT').ABSENT

    def __init__(self, params):
        self.params = params
        self.valid_param_indexes = range(0, len(self.params))

    def __repr__(self):
        return f'<ANY OF {self.params}>'

    def __getitem__(self, key):
        values = []
        for param_index in self.valid_param_indexes:
            param = self.params[param_index]
            if key in param:
                values.append(param[key])
            else:
                values.append(self.ABSENT)
        return ANY_VALUE(self, values)

    def keys(self):
        result = []
        for param_index in self.valid_param_indexes:
            param = self.params[param_index]
            for key in param:
                if key not in result:
                    result.append(key)
        return result

    def items(self):
        for key in self.keys():
            any_value = self[key]
            if all(value == self.ABSENT for value in any_value.values):
                continue
            yield key, any_value


def test_copy_resource_s3(tmp_path, mocker):
    """Test copy_resource_s3 script"""

    resource_sha = 'fffe62254ef635871589a848b65db441318171eb'
    resource_a_name = resource_sha
    resource_b_name = resource_sha + '.json'

    book_dir = tmp_path / "col11762"
    book_dir.mkdir()
    resources_dir = book_dir / "resources"
    resources_dir.mkdir()

    resource_a = resources_dir / resource_a_name
    resource_b = resources_dir / resource_b_name

    # copy over the test data a to the tmp_path
    resource_a_data = os.path.join(TEST_DATA_DIR, resource_a_name)
    resource_a_data = open(resource_a_data, "rb").read()
    resource_a.write_bytes(resource_a_data)

    # copy over the test data b to the tmp_path
    resource_b_data = os.path.join(TEST_DATA_DIR, resource_b_name)
    resource_b_data = open(resource_b_data, "rb").read()
    resource_b.write_bytes(resource_b_data)

    bucket = 'distribution-bucket-1234'
    prefix = 'master/resources'

    key_a = prefix + '/' + resource_a_name
    key_b = prefix + '/' + resource_sha + '-unused.json'

    s3_client = boto3.client('s3')
    s3_stubber = botocore.stub.Stubber(s3_client)
    s3_stubber.add_response(
        'list_objects',
        {},
        expected_params={
            'Bucket': bucket,
            'Prefix': prefix + '/',
            'Delimiter': '/'
        }
    )
    for _ in [0, 1]:
        s3_stubber.add_response(
            "put_object",
            {},
            expected_params=ANY_PARAM([
                {
                    'Body':  botocore.stub.ANY,
                    'Bucket': bucket,
                    'ContentType': 'application/json',
                    'Key': key_b,
                },
                {
                    'Body':  botocore.stub.ANY,
                    'Bucket': bucket,
                    'ContentType': 'image/jpeg',
                    'Key': key_a,
                    'Metadata': {'height': '192', 'width': '241'},
                },
            ])
        )
    s3_stubber.activate()

    mocked_session = boto3.session.Session
    mocked_session.client = mocker.MagicMock(return_value=s3_client)
    mocker.patch(
        'boto3.session.Session',
        mocked_session
    )
    mocker.patch(
        'sys.argv',
        ['',
         resources_dir,
         bucket,
         prefix]
    )

    os.environ['AWS_ACCESS_KEY_ID'] = 'dummy-key'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'dummy-secret'

    copy_resources_s3.main()

    del os.environ['AWS_ACCESS_KEY_ID']
    del os.environ['AWS_SECRET_ACCESS_KEY']

    s3_stubber.assert_no_pending_responses()
    s3_stubber.deactivate()


def test_copy_resource_s3_environment(tmp_path, mocker):
    """Test copy_resource_s3 script errors without aws credentials"""

    book_dir = tmp_path / "col11762"
    book_dir.mkdir()
    resources_dir = book_dir / "resources"
    resources_dir.mkdir()

    dist_bucket = 'distribution-bucket-1234'
    dist_bucket_prefix = 'master/resources'

    s3_client = boto3.client('s3')
    s3_stubber = botocore.stub.Stubber(s3_client)
    s3_stubber.add_response(
        'list_objects',
        {},
        expected_params={
            'Bucket': dist_bucket,
            'Prefix': dist_bucket_prefix + '/',
            'Delimiter': '/'
        }
    )
    s3_stubber.activate()

    mocked_session = boto3.session.Session
    mocked_session.client = mocker.MagicMock(return_value=s3_client)

    mocker.patch(
        'boto3.session.Session',
        mocked_session
    )

    mocker.patch(
        'sys.argv',
        ['',
         resources_dir,
         dist_bucket,
         dist_bucket_prefix]
    )

    with pytest.raises(OSError):
        copy_resources_s3.main()

    s3_stubber.assert_no_pending_responses()
    s3_stubber.deactivate()


def test_s3_existence(tmp_path, mocker):
    """Test copy_resource_s3.test_s3_existence function"""

    resource_name = "fffe62254ef635871589a848b65db441318171eb.json"
    bucket = 'distribution-bucket-1234'
    key = 'master/resources/' + resource_name
    resource = os.path.join(TEST_DATA_DIR, resource_name)
    test_resource = {
        "input_metadata_file": resource,
        "output_s3": key,
    }

    aws_key = 'dummy-key'
    aws_secret = 'dummy-secret'
    aws_token = None

    s3_client = boto3.client('s3')
    s3_stubber = botocore.stub.Stubber(s3_client)
    s3_stubber.add_response(
        "head_object",
        {"ETag": '14e273e6f416c4b90a071f59ac01206a'},
        expected_params={
            "Bucket": bucket,
            "Key": key,
        },
    )
    s3_stubber.activate()

    upload_resource = copy_resources_s3.check_s3_existence(
        aws_key, aws_secret, aws_token,
        bucket, test_resource,
        disable_check=False
    )

    test_input_metadata = test_resource['input_metadata_file']
    test_output_s3 = test_resource['output_s3']
    uploaded_input_metadata = upload_resource['input_metadata_file']
    uploaded_output_s3 = upload_resource['output_s3']

    assert test_input_metadata == uploaded_input_metadata
    assert test_output_s3 == uploaded_output_s3

    s3_stubber.deactivate()


def test_s3_existence_404(tmp_path, mocker):
    """Test copy_resource_s3.test_s3_existence
    function errors with wrong file name"""

    resource_name = "fffe62254ef635871589a848b65db441318171eb"
    bucket = 'distribution-bucket-1234'
    key = 'master/resources/' + resource_name

    wrong_resource = "babybeluga.json"
    test_resource = os.path.join(TEST_DATA_DIR, wrong_resource)
    resource_for_test = {
        "input_metadata_file": test_resource,
        "output_s3": key,
    }

    aws_key = 'dummy-key'
    aws_secret = 'dummy-secret'
    aws_token = None

    s3_client = boto3.client('s3')
    s3_stubber = botocore.stub.Stubber(s3_client)
    s3_stubber.activate()

    with pytest.raises(FileNotFoundError):
        copy_resources_s3.check_s3_existence(
            aws_key, aws_secret, aws_token,
            bucket, resource_for_test,
            disable_check=False
        )

    s3_stubber.assert_no_pending_responses()
    s3_stubber.deactivate()


def test_upload_docx(tmp_path, mocker):
    """Test upload-docx script"""

    mock_creds = mocker.Mock(spec=google.auth.credentials.Credentials)
    parent_google_folder_id = "parentfolderID"
    book_folder = "How to be awesome"
    book_folder_id = "bookfolderID"

    # Test find_or_create_folder_by_name when folder does not exist
    request_builder = RequestMockBuilder(
        {
            "drive.files.list": (None, json.dumps({"files": []})),
            "drive.files.create": (
                None,
                json.dumps({"id": book_folder_id}),
                {
                    "name": book_folder,
                    "parents": [parent_google_folder_id],
                    "mimeType": "application/vnd.google-apps.folder"
                }
            )
        },
        check_unexpected=True
    )

    mock_drive_service = build(
        "drive", "v3", requestBuilder=request_builder, credentials=mock_creds
    )

    result = upload_docx.find_or_create_folder_by_name(
        mock_drive_service,
        parent_google_folder_id,
        book_folder
    )
    assert result == book_folder_id

    # Test find_or_create_folder_by_name when multiple folders returned
    request_builder = RequestMockBuilder(
        {
            "drive.files.list": (
                None,
                json.dumps({"files": [{"id": ""}, {"id": ""}]})
            )
        },
        check_unexpected=True
    )

    mock_drive_service = build(
        "drive", "v3", requestBuilder=request_builder, credentials=mock_creds
    )

    with pytest.raises(Exception):
        upload_docx.find_or_create_folder_by_name(
            mock_drive_service,
            parent_google_folder_id,
            book_folder
        )

    # Test find_or_create_folder_by_name when folder exists
    request_builder = RequestMockBuilder(
        {
            "drive.files.list": (
                None,
                json.dumps({"files": [{"id": book_folder_id}]})
            )
        },
        check_unexpected=True
    )

    mock_drive_service = build(
        "drive", "v3", requestBuilder=request_builder, credentials=mock_creds
    )

    result = upload_docx.find_or_create_folder_by_name(
        mock_drive_service,
        parent_google_folder_id,
        book_folder
    )

    assert result == book_folder_id

    # Test get_gdocs_in_folder
    request_builder = RequestMockBuilder(
        {
            "drive.files.list": (
                None,
                json.dumps({
                    "files": [
                        {"id": "gdoc1", "name": "gdoc1"},
                        {"id": "gdoc2", "name": "gdoc2"}
                    ]
                })
            )
        },
        check_unexpected=True
    )

    mock_drive_service = build(
        "drive", "v3", requestBuilder=request_builder, credentials=mock_creds
    )

    result = upload_docx.get_gdocs_in_folder(
        mock_drive_service,
        book_folder_id
    )

    assert result == [
        {"id": "gdoc1", "name": "gdoc1"},
        {"id": "gdoc2", "name": "gdoc2"}
    ]

    # Test upsert_docx_to_folder
    input_dir = tmp_path / "docx-book" / "col12345" / "docx"
    input_dir.mkdir(parents=True)
    input_docx = []
    for doc_name in ["chapter1", "chapter2"]:
        docx = input_dir / f"{doc_name}.docx"
        docx.write_text("Test")
        input_docx.append(docx)

    request_builder = RequestMockBuilder(
        {
            "drive.files.list": (
                None,
                json.dumps({
                    "files": [
                        {"id": "ch1exists", "name": "chapter1"}
                    ]
                })
            ),
            "drive.files.create": (
                None,
                json.dumps({"id": "ch2new"})
            ),
            "drive.files.update": (
                None,
                json.dumps({})
            )
        },
        check_unexpected=True
    )

    mock_drive_service = build(
        "drive", "v3", requestBuilder=request_builder, credentials=mock_creds
    )

    results = upload_docx.upsert_docx_to_folder(
        mock_drive_service,
        input_docx,
        book_folder_id
    )

    assert results == [
        {"id": "ch1exists", "name": "chapter1"},
        {"id": "ch2new", "name": "chapter2"},
    ]


def test_fetch_map_resources(tmp_path, mocker):
    """Test fetch-map-resources script"""
    book_dir = tmp_path / "book_slug/fetched-book-group/raw/modules"
    original_resources_dir = tmp_path / "book_slug/fetched-book-group/raw/media"
    original_interactive_dir = tmp_path / "book_slug/fetched-book-group/raw/media/interactive"
    resources_parent_dir = tmp_path / "book_slug"
    resources_dir = resources_parent_dir / "resources"
    unused_resources_dir = tmp_path / "unused-resources"

    book_dir.mkdir(parents=True)
    original_resources_dir.mkdir(parents=True)
    original_interactive_dir.mkdir(parents=True)

    interactive = original_interactive_dir / "index.xhtml"
    interactive_content = (
        '<!DOCTYPE html>'
        '<html xmlns="http://www.w3.org/1999/xhtml" lang="en-US">'
        '<body>'
        '<p>Hello! I am an interactive. I should eventually have CSS and javascript</p>'
        '</body>'
        '</html>'
    )
    interactive.write_text(interactive_content)

    resources_parent_dir.mkdir(exist_ok=True)
    unused_resources_dir.mkdir()

    image_src = original_resources_dir / "image_src.svg"
    image_src = original_resources_dir / "image_src.svg"
    image_unused = original_resources_dir / "image_unused.svg"

    # libmagic yields image/svg without the xml declaration
    image_src_content = ('<?xml version=1.0 ?>'
                         '<svg height="30" width="120">'
                         '<text x="0" y="15" fill="red">'
                         'checksum me!'
                         '</text>'
                         '</svg>')
    image_src_sha1_expected = "527617b308327b8773c5105edc8c28bcbbe62553"
    image_src_md5_expected = "420c64c8dbe981f216989328f9ad97e7"
    image_src.write_text(image_src_content)
    image_src_meta = f"{image_src_sha1_expected}.json"

    # libmagic yields image/svg without the xml declaration
    image_unused_content = ('<?xml version=1.0 ?>'
                            '<svg height="30" width="120">'
                            '<text x="0" y="15" fill="red">'
                            'nope.'
                            '</text>'
                            '</svg>')
    image_unused.write_text(image_unused_content)

    module_0001_dir = book_dir / "m00001"
    module_0001_dir.mkdir()
    module_00001 = book_dir / "m00001/index.cnxml"
    module_00001_content = (
        '<document xmlns="http://cnx.rice.edu/cnxml">'
        '<content>'
        '<image src="../../media/image_src.svg"/>'
        '<image src="../../media/image_missing.jpg"/>'
        '<image src="../../media/image_src.svg"/>'
        '<iframe src="../../media/interactive/index.xhtml"/>'
        '</content>'
        '</document>'
    )
    module_00001.write_text(module_00001_content)

    mocker.patch(
        "sys.argv",
        ["", book_dir, original_resources_dir, resources_parent_dir, unused_resources_dir]
    )
    fetch_map_resources.main()

    assert json.load((resources_dir / image_src_meta).open()) == {
        'mime_type': 'image/svg+xml',
        'original_name': 'image_src.svg',
        # AWS needs the MD5 quoted inside the string json value.
        # Despite looking like a mistake, this is correct behavior.
        's3_md5': f'"{image_src_md5_expected}"',
        'sha1': image_src_sha1_expected
    }
    assert set(file.name for file in resources_dir.glob('**/*')) == set([
        image_src_sha1_expected,
        image_src_meta,
        "interactive",
        "index.xhtml"
    ])
    tree = etree.parse(str(module_00001))
    expected = (
        f'<document xmlns="http://cnx.rice.edu/cnxml">'
        f'<content>'
        f'<image src="../resources/{image_src_sha1_expected}"/>'
        f'<image src="../../media/image_missing.jpg"/>'
        f'<image src="../resources/{image_src_sha1_expected}"/>'
        f'<iframe src="../resources/interactive/index.xhtml"/>'
        f'</content>'
        f'</document>'
    )
    assert etree.tostring(tree, encoding="utf8") == expected.encode("utf8")
    assert set(file.name for file in unused_resources_dir.glob('**/*')) == set([
        "image_unused.svg",
    ])

    assert(resources_dir.is_dir())


def test_fetch_update_metadata(tmp_path, mocker):
    """Test fetch-update-metadata script"""
    book_dir = tmp_path / "book_slug/fetched-book-group/raw/"
    modules_dir = book_dir / "modules"
    collections_dir = book_dir / "collections"
    canonical_file = book_dir / "canonical.json"
    repo_path = tmp_path / ".repo"
    modules_dir.mkdir(parents=True)
    collections_dir.mkdir(parents=True)
    repo_path.mkdir()

    canonical_content = json.dumps(['test'])
    canonical_file.write_text(canonical_content)

    coll_file = collections_dir / "test.collection.xml"
    coll_content = (
        '<col:collection xmlns:col="http://cnx.rice.edu/collxml">'
        '<col:metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">'
        '<md:uuid>some-random-uuid</md:uuid>'
        '</col:metadata>'
        '<col:module document="m00001" />'
        '</col:collection>'
    )
    coll_file.write_text(coll_content)

    module_00001_dir = modules_dir / "m00001"
    module_00001_dir.mkdir()
    module_00001 = modules_dir / "m00001/index.cnxml"
    module_00001_content = (
        '<document xmlns="http://cnx.rice.edu/cnxml">'
        '<metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">'
        '</metadata>'
        '</document>'
    )
    module_00001.write_text(module_00001_content)

    orphan_module_00002_dir = modules_dir / "m00002"
    orphan_module_00002_dir.mkdir()
    orphan_module_00002 = modules_dir / "m00002/index.cnxml"
    orphan_module_00002_content = (
        '<document xmlns="http://cnx.rice.edu/cnxml">'
        '<metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5"/>'
        '</document>'
    )
    orphan_module_00002.write_text(orphan_module_00002_content)

    repo_mock = mocker.MagicMock()
    commit_mock = repo_mock().revparse_single()
    commit_mock.commit_time = 1610500380
    commit_mock.id = "somegitsha"
    ref1_mock = mocker.MagicMock()
    ref1_mock.name = "refs/tags/somegittag"
    ref1_mock.target = "somegitsha"
    ref1_mock.shorthand = "somegittag"
    repo_mock().references.objects = [ref1_mock]
    mocker.patch(
        "sys.argv",
        ["", repo_path, modules_dir, collections_dir, ref1_mock.shorthand, canonical_file]
    )
    mocker.patch(
        "bakery_scripts.fetch_update_metadata.Repository",
        repo_mock
    )
    fetch_update_metadata.main()

    tree = etree.parse(str(module_00001))
    expected = (
        '<document xmlns="http://cnx.rice.edu/cnxml">'
        '<metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">'
        '<md:revised>2021-01-13T01:13:00+00:00</md:revised>\n'
        '<md:canonical-book-uuid>some-random-uuid</md:canonical-book-uuid>\n'
        '</metadata>'
        '</document>'
    )
    assert etree.tostring(tree, encoding="utf8") == expected.encode("utf8")

    tree = etree.parse(str(orphan_module_00002))
    # Orphans should be unmodified
    expected = orphan_module_00002_content
    assert etree.tostring(tree, encoding="utf8") == expected.encode("utf8")

    tree = etree.parse(str(coll_file))
    expected = (
        '<col:collection xmlns:col="http://cnx.rice.edu/collxml">'
        '<col:metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">'
        '<md:uuid>some-random-uuid</md:uuid>'
        '<md:revised>2021-01-13T01:13:00+00:00</md:revised>\n'
        '<md:version>somegittag</md:version>\n'
        '</col:metadata>'
        '<col:module document="m00001"/>'
        '</col:collection>'
    )
    assert etree.tostring(tree, encoding="utf8") == expected.encode("utf8")


def test_fetch_update_metadata_canonical_ordering(tmp_path, mocker):
    """Test canonical ordering in fetch-update-metadata script"""
    book_dir = tmp_path / "book_slug/fetched-book-group/raw/"
    modules_dir = book_dir / "modules"
    collections_dir = book_dir / "collections"
    canonical_file = book_dir / "canonical.json"
    repo_path = tmp_path / ".repo"
    modules_dir.mkdir(parents=True)
    collections_dir.mkdir(parents=True)
    repo_path.mkdir()

    canonical_content = json.dumps(['test0', 'test1'])
    canonical_file.write_text(canonical_content)

    coll_file_0 = collections_dir / "test0.collection.xml"
    coll_content_0 = (
        '<col:collection xmlns:col="http://cnx.rice.edu/collxml">'
        '<col:metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">'
        '<md:uuid>some-random-uuid-0</md:uuid>'
        '</col:metadata>'
        '<col:module document="m00001" />'
        '<col:module document="m00002" />'
        '</col:collection>'
    )
    coll_file_0.write_text(coll_content_0)

    coll_file_1 = collections_dir / "test1.collection.xml"
    coll_content_1 = (
        '<col:collection xmlns:col="http://cnx.rice.edu/collxml">'
        '<col:metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">'
        '<md:uuid>some-random-uuid-1</md:uuid>'
        '</col:metadata>'
        '<col:module document="m00002" />'
        '<col:module document="m00003" />'
        '</col:collection>'
    )
    coll_file_1.write_text(coll_content_1)

    module_00001_dir = modules_dir / "m00001"
    module_00001_dir.mkdir()
    module_00001 = modules_dir / "m00001/index.cnxml"
    module_00001_content = (
        '<document xmlns="http://cnx.rice.edu/cnxml">'
        '<metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">'
        '<md:canonical-book-uuid>garbage</md:canonical-book-uuid>'
        '</metadata>'
        '</document>'
    )
    module_00001.write_text(module_00001_content)

    module_00002_dir = modules_dir / "m00002"
    module_00002_dir.mkdir()
    module_00002 = modules_dir / "m00002/index.cnxml"
    module_00002_content = (
        '<document xmlns="http://cnx.rice.edu/cnxml">'
        '<metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">'
        '</metadata>'
        '</document>'
    )
    module_00002.write_text(module_00002_content)

    module_00003_dir = modules_dir / "m00003"
    module_00003_dir.mkdir()
    module_00003 = modules_dir / "m00003/index.cnxml"
    module_00003_content = (
        '<document xmlns="http://cnx.rice.edu/cnxml">'
        '<metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">'
        '</metadata>'
        '</document>'
    )
    module_00003.write_text(module_00003_content)

    repo_mock = mocker.MagicMock()
    commit_mock = repo_mock().revparse_single()
    commit_mock.commit_time = 1610500380
    commit_mock.id = "somegitsha"
    ref1_mock = mocker.MagicMock()
    ref1_mock.name = "refs/tags/somegittag"
    ref1_mock.target = "somegitsha"
    ref1_mock.shorthand = "somegittag"
    repo_mock().references.objects = [ref1_mock]
    mocker.patch(
        "sys.argv",
        ["", repo_path, modules_dir, collections_dir, ref1_mock.shorthand, canonical_file]
    )
    mocker.patch(
        "bakery_scripts.fetch_update_metadata.Repository",
        repo_mock
    )
    fetch_update_metadata.main()

    tree = etree.parse(str(module_00001))
    expected = (
        '<document xmlns="http://cnx.rice.edu/cnxml">'
        '<metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">'
        '<md:revised>2021-01-13T01:13:00+00:00</md:revised>\n'
        '<md:canonical-book-uuid>some-random-uuid-0</md:canonical-book-uuid>\n'
        '</metadata>'
        '</document>'
    )
    assert etree.tostring(tree, encoding="utf8") == expected.encode("utf8")

    tree = etree.parse(str(module_00002))
    expected = (
        '<document xmlns="http://cnx.rice.edu/cnxml">'
        '<metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">'
        '<md:revised>2021-01-13T01:13:00+00:00</md:revised>\n'
        '<md:canonical-book-uuid>some-random-uuid-0</md:canonical-book-uuid>\n'
        '</metadata>'
        '</document>'
    )
    assert etree.tostring(tree, encoding="utf8") == expected.encode("utf8")

    tree = etree.parse(str(module_00003))
    expected = (
        '<document xmlns="http://cnx.rice.edu/cnxml">'
        '<metadata xmlns:md="http://cnx.rice.edu/mdml" mdml-version="0.5">'
        '<md:revised>2021-01-13T01:13:00+00:00</md:revised>\n'
        '<md:canonical-book-uuid>some-random-uuid-1</md:canonical-book-uuid>\n'
        '</metadata>'
        '</document>'
    )
    assert etree.tostring(tree, encoding="utf8") == expected.encode("utf8")


def test_fetch_update_metadata_determine_book_version(mocker):
    """Tests for determine_book_version helper function"""
    repo_mock = mocker.MagicMock()
    commit_mock = mocker.MagicMock()
    commit_mock.id = "123456789abcdef"
    # ref1 mock
    ref1_mock = mocker.MagicMock()
    ref1_mock.name = "refs/tags/tag1"
    ref1_mock.target = "123456789abcdef"
    ref1_mock.shorthand = "tag1"
    # ref2 mock
    ref2_mock = mocker.MagicMock()
    ref2_mock.name = "refs/tags/tag2"
    ref2_mock.target = "foobar"
    ref2_mock.shorthand = "tag2"
    # ref 3 mock
    ref3_mock = mocker.MagicMock()
    ref3_mock.name = "refs/tags/tag3"
    ref3_mock.target = "123456789abcdef"
    ref3_mock.shorthand = "tag3"

    # Test when there are no matching tags
    repo_mock.references.objects = [ref2_mock]

    version = fetch_update_metadata.determine_book_version(
        "branch", repo_mock, commit_mock
    )
    assert version == "1234567"

    # Test when there is one matching tag and it matches the reference
    repo_mock.references.objects = [ref1_mock, ref2_mock]

    version = fetch_update_metadata.determine_book_version(
        "tag1", repo_mock, commit_mock
    )
    assert version == "tag1"

    # Test when there is one matching tag and it doesn't match the reference
    repo_mock.references.objects = [ref1_mock, ref2_mock]

    version = fetch_update_metadata.determine_book_version(
        "branch", repo_mock, commit_mock
    )
    assert version == "tag1"

    # Test when there is more than one matching tag, neither of which match
    # the reference
    repo_mock.references.objects = [ref1_mock, ref2_mock, ref3_mock]

    version = fetch_update_metadata.determine_book_version(
        "branch", repo_mock, commit_mock
    )
    assert version == "1234567"

    # Test when there is more than one matching tag, one of which matches
    # the reference
    repo_mock.references.objects = [ref1_mock, ref2_mock, ref3_mock]

    version = fetch_update_metadata.determine_book_version(
        "tag3", repo_mock, commit_mock
    )
    assert version == "tag3"


def test_link_single(tmp_path, mocker):
    """Test link-single script"""
    baked_dir = tmp_path / "baked-book-group"
    baked_dir.mkdir()
    baked_meta_dir = tmp_path / "baked-book-metadata-group"
    baked_meta_dir.mkdir()
    source_book_slug = "book1"
    linked_xhtml = tmp_path / "book1.linked.xhtml"

    book1_baked_content = """
        <html xmlns="http://www.w3.org/1999/xhtml" lang="en">
        <body itemscope="itemscope" itemtype="http://schema.org/Book">
        <div data-type="metadata" style="display: none;">
        <h1 data-type="document-title" itemprop="name">Book1</h1>
        <span data-type="slug" data-value="book1"></span>
        <span data-type="cnx-archive-uri"
            data-value="1ba7e813-2d8a-4b73-87a1-876cfb5e7b58@version"></span>
        </div>
        <nav id="toc">
        <ol>
        <li cnx-archive-uri="9f049b16-15e9-4725-8c8b-4908a3e2be5e@">
        <a href="">Page1</a>
        </li>
        <li cnx-archive-uri="cffe96ff-cab6-453c-9996-ed6abe5d9b13@">
        <a href="">Page2</a>
        </li>
        </ol>
        </nav>
        <div data-type="page" id="9f049b16-15e9-4725-8c8b-4908a3e2be5e">
        <div data-type="metadata" style="display: none;">
        <h1 data-type="document-title" itemprop="name">Page1</h1>
        <span data-type="canonical-book-uuid" data-value="1ba7e813-2d8a-4b73-87a1-876cfb5e7b58"/>
        </div>
        <p><a id="l1"
            href="/contents/4aa9351c-019f-4c06-bb40-d58262ea7ec7"
            >Inter-book module link</a></p>
        <p><a id="l2"
            href="/contents/2e51553f-fde8-43a3-8191-fd8b493a6cfa#foobar"
            >Inter-book module link with fragment</a></p>
        </div>
        <div data-type="page" id="cffe96ff-cab6-453c-9996-ed6abe5d9b13e">
        <div data-type="metadata" style="display: none;">
        <h1 data-type="document-title" itemprop="name">Page2</h1>
        <span data-type="canonical-book-uuid" data-value="1ba7e813-2d8a-4b73-87a1-876cfb5e7b58"/>
        </div>
        <p><a id="l3"
            href="/contents/9f049b16-15e9-4725-8c8b-4908a3e2be5e"
            >Intra-book module link</a></p>
        </div>
        </body>
        </html>
    """
    book1_baked_meta_content = {
        "1ba7e813-2d8a-4b73-87a1-876cfb5e7b58@version": {
            "id": "1ba7e813-2d8a-4b73-87a1-876cfb5e7b58",
            "slug": "book1",
            "tree": {
                "id": "1ba7e813-2d8a-4b73-87a1-876cfb5e7b58@version",
                "slug": "book1",
                "contents": [
                    {
                        "id": "9f049b16-15e9-4725-8c8b-4908a3e2be5e@",
                        "slug": "book1-page1"
                    },
                    {
                        "id": "cffe96ff-cab6-453c-9996-ed6abe5d9b13e@",
                        "slug": "book1-page2"
                    }
                ]
            }
        }
    }
    book1_baked = baked_dir / "book1.baked.xhtml"
    book1_baked_meta = baked_meta_dir / "book1.baked-metadata.json"
    book1_baked.write_text(book1_baked_content)
    book1_baked_meta.write_text(json.dumps(book1_baked_meta_content))

    book2_baked_content = """
        <html xmlns="http://www.w3.org/1999/xhtml" lang="en">
        <body itemscope="itemscope" itemtype="http://schema.org/Book">
        <div data-type="metadata" style="display: none;">
        <h1 data-type="document-title" itemprop="name">Book2</h1>
        <span data-type="slug" data-value="book2"></span>
        <span data-type="cnx-archive-uri"
            data-value="3c321f43-1da5-4c7b-91d1-abca2dd8ab8f@version"></span>
        </div>
        <nav id="toc">
        <ol>
        <li cnx-archive-uri="4aa9351c-019f-4c06-bb40-d58262ea7ec7@">
        <a href="">Page1</a>
        </li>
        <li cnx-archive-uri="2e51553f-fde8-43a3-8191-fd8b493a6cfa@">
        <a href="">Page2</a>
        </li>
        </ol>
        </nav>
        <div data-type="page" id="4aa9351c-019f-4c06-bb40-d58262ea7ec7">
        <div data-type="metadata" style="display: none;">
        <h1 data-type="document-title" itemprop="name">Page1</h1>
        <span data-type="canonical-book-uuid" data-value="3c321f43-1da5-4c7b-91d1-abca2dd8ab8f"/>
        </div>
        </div>
        <div data-type="page" id="2e51553f-fde8-43a3-8191-fd8b493a6cfa">
        <div data-type="metadata" style="display: none;">
        <h1 data-type="document-title" itemprop="name">Page2</h1>
        <span data-type="canonical-book-uuid" data-value="3c321f43-1da5-4c7b-91d1-abca2dd8ab8f"/>
        </div>
        </div>
        </body>
        </html>
    """
    book2_baked_meta_content = {
        "3c321f43-1da5-4c7b-91d1-abca2dd8ab8f@version": {
            "id": "3c321f43-1da5-4c7b-91d1-abca2dd8ab8f",
            "slug": "book2",
            "tree": {
                "id": "3c321f43-1da5-4c7b-91d1-abca2dd8ab8f@version",
                "slug": "book2",
                "contents": [
                    {
                        "id": "4aa9351c-019f-4c06-bb40-d58262ea7ec7@",
                        "slug": "book2-page1"
                    },
                    {
                        "id": "2e51553f-fde8-43a3-8191-fd8b493a6cfa@",
                        "slug": "book2-page2"
                    }
                ]
            }
        }
    }
    book2_baked = baked_dir / "book2.baked.xhtml"
    book2_baked_meta = baked_meta_dir / "book2.baked-metadata.json"
    book2_baked.write_text(book2_baked_content)
    book2_baked_meta.write_text(json.dumps(book2_baked_meta_content))

    mocker.patch(
        "sys.argv",
        ["", str(baked_dir), str(baked_meta_dir), source_book_slug, str(linked_xhtml)]
    )
    link_single.main()

    expected_links = [
        [
            ("id", "l1"),
            ("href",
             "./3c321f43-1da5-4c7b-91d1-abca2dd8ab8f:4aa9351c-019f-4c06-bb40-d58262ea7ec7.xhtml"),
            ("data-book-uuid", "3c321f43-1da5-4c7b-91d1-abca2dd8ab8f"),
            ("data-book-slug", "book2"),
            ("data-page-slug", "book2-page1"),
        ],
        [
            ("id", "l2"),
            ("href",
             "./3c321f43-1da5-4c7b-91d1-abca2dd8ab8f:"
             "2e51553f-fde8-43a3-8191-fd8b493a6cfa.xhtml#foobar"),
            ("data-book-uuid", "3c321f43-1da5-4c7b-91d1-abca2dd8ab8f"),
            ("data-book-slug", "book2"),
            ("data-page-slug", "book2-page2"),
        ],
        [
            ("id", "l3"),
            ("href", "/contents/9f049b16-15e9-4725-8c8b-4908a3e2be5e")
        ]
    ]

    tree = etree.parse(str(linked_xhtml))

    parsed_links = tree.xpath(
        '//x:a[@href and starts-with(@href, "/contents/") or starts-with(@href, "./")]',
        namespaces={"x": "http://www.w3.org/1999/xhtml"},
    )

    check_links = [
        link.items() for link in parsed_links
    ]

    assert check_links == expected_links


def test_link_single_with_flag(tmp_path, mocker):
    """Test link-single script"""
    baked_dir = tmp_path / "baked-book-group"
    baked_dir.mkdir()
    baked_meta_dir = tmp_path / "baked-book-metadata-group"
    baked_meta_dir.mkdir()
    source_book_slug = "book1"
    linked_xhtml = tmp_path / "book1.linked.xhtml"

    book1_baked_content = """
        <html xmlns="http://www.w3.org/1999/xhtml" lang="en">
        <body itemscope="itemscope" itemtype="http://schema.org/Book">
        <div data-type="metadata" style="display: none;">
        <h1 data-type="document-title" itemprop="name">Book1</h1>
        <span data-type="slug" data-value="book1"></span>
        <span data-type="cnx-archive-uri"
            data-value="1ba7e813-2d8a-4b73-87a1-876cfb5e7b58@version"></span>
        </div>
        <nav id="toc">
        <ol>
        <li cnx-archive-uri="9f049b16-15e9-4725-8c8b-4908a3e2be5e@">
        <a href="">Page1</a>
        </li>
        <li cnx-archive-uri="cffe96ff-cab6-453c-9996-ed6abe5d9b13@">
        <a href="">Page2</a>
        </li>
        <li cnx-archive-uri="cea7795c-c138-4356-a221-f5eed5ad1adc@">
        <a href="">Page3</a>
        </li>
        </ol>
        </nav>
        <div data-type="page" id="9f049b16-15e9-4725-8c8b-4908a3e2be5e">
        <div data-type="metadata" style="display: none;">
        <h1 data-type="document-title" itemprop="name">Page1</h1>
        <span data-type="canonical-book-uuid" data-value="1ba7e813-2d8a-4b73-87a1-876cfb5e7b58"/>
        </div>
        <p><a id="l1"
            href="/contents/4aa9351c-019f-4c06-bb40-d58262ea7ec7"
            >Inter-book module link</a></p>
        <p><a id="l2"
            href="/contents/2e51553f-fde8-43a3-8191-fd8b493a6cfa#foobar"
            >Inter-book module link with fragment</a></p>
        </div>
        <div data-type="page" id="cffe96ff-cab6-453c-9996-ed6abe5d9b13e">
        <div data-type="metadata" style="display: none;">
        <h1 data-type="document-title" itemprop="name">Page2</h1>
        <span data-type="canonical-book-uuid" data-value="1ba7e813-2d8a-4b73-87a1-876cfb5e7b58"/>
        </div>
        <p><a id="l3"
            href="/contents/9f049b16-15e9-4725-8c8b-4908a3e2be5e"
            >Intra-book module link</a></p>
        <p><a id="l4"
            href="/contents/cea7795c-c138-4356-a221-f5eed5ad1adc"
            >Intra-book module link for shared page with outside canonical</a></p>
        </div>
        <div data-type="page" id="cea7795c-c138-4356-a221-f5eed5ad1adc">
        <div data-type="metadata" style="display: none;">
        <h1 data-type="document-title" itemprop="name">Page3</h1>
        <span data-type="canonical-book-uuid" data-value="6a88da29-8d6a-4139-bafc-e179be9b241d"/>
        </div>
        <p>Content</p>
        </div>
        </body>
        </html>
    """
    book1_baked_meta_content = {
        "1ba7e813-2d8a-4b73-87a1-876cfb5e7b58@version": {
            "id": "1ba7e813-2d8a-4b73-87a1-876cfb5e7b58",
            "slug": "book1",
            "tree": {
                "id": "1ba7e813-2d8a-4b73-87a1-876cfb5e7b58@version",
                "slug": "book1",
                "contents": [
                    {
                        "id": "9f049b16-15e9-4725-8c8b-4908a3e2be5e@",
                        "slug": "book1-page1"
                    },
                    {
                        "id": "cffe96ff-cab6-453c-9996-ed6abe5d9b13e@",
                        "slug": "book1-page2"
                    },
                    {
                        "id": "cea7795c-c138-4356-a221-f5eed5ad1adc@",
                        "slug": "book1-page3"
                    }
                ]
            }
        }
    }
    book1_baked = baked_dir / "book1.baked.xhtml"
    book1_baked_meta = baked_meta_dir / "book1.baked-metadata.json"
    book1_baked.write_text(book1_baked_content)
    book1_baked_meta.write_text(json.dumps(book1_baked_meta_content))

    mocker.patch(
        "sys.argv",
        ["", str(baked_dir), str(baked_meta_dir), source_book_slug, str(linked_xhtml),
         "--mock-otherbook"]
    )
    link_single.main()

    expected_links = [
        [
            ("id", "l1"),
            ("href",
             "mock-inter-book-link"),
            ("data-book-uuid",
             "mock-inter-book-uuid")
        ],
        [
            ("id", "l2"),
            ("href",
             "mock-inter-book-link"),
            ("data-book-uuid",
             "mock-inter-book-uuid")
        ],
        [
            ("id", "l3"),
            ("href", "/contents/9f049b16-15e9-4725-8c8b-4908a3e2be5e")
        ],
        [
            ("id", "l4"),
            ("href", "mock-inter-book-link"),
            ("data-book-uuid",
             "mock-inter-book-uuid")
        ]
    ]

    tree = etree.parse(str(linked_xhtml))

    parsed_links = tree.xpath(
        '//x:a[@href and starts-with(@href, "mock-inter-book-link") or starts-with(@href, "./") '
        'or starts-with(@href, "/contents")]',
        namespaces={"x": "http://www.w3.org/1999/xhtml"},
    )

    check_links = [
        link.items() for link in parsed_links
    ]

    assert check_links == expected_links

    with pytest.raises(
        Exception,
        match=r'Could not find canonical book'
    ):
        mocker.patch(
            "sys.argv",
            ["", str(baked_dir), str(baked_meta_dir), source_book_slug, str(linked_xhtml)]
        )
        link_single.main()


def test_ensure_isoformat():
    """Test ensure_isoformat utility function"""
    assert utils.ensure_isoformat("2021-03-22T14:14:33.17588-05:00") == \
        "2021-03-22T14:14:33.17588-05:00"
    assert utils.ensure_isoformat("2021-03-23T11:34:33.989606-05:00") == \
        "2021-03-23T11:34:33.989606-05:00"
    assert utils.ensure_isoformat("2018/10/01 14:04:45 -0500") == \
        "2018-10-01T14:04:45-05:00"
    assert utils.ensure_isoformat("2020/12/21 16:05:52.185 US/Central") == \
        "2020-12-21T16:05:52.185000-06:00"
    assert utils.ensure_isoformat("2020/09/15 13:39:55.802 GMT-5") == \
        "2020-09-15T13:39:55.802000-05:00"
    assert utils.ensure_isoformat("2018/09/25 06:57:44 GMT-5") == \
        "2018-09-25T06:57:44-05:00"
    with pytest.raises(
        Exception,
        match="Could not convert non ISO8601 timestamp: unexpectedtimeformat"
    ):
        utils.ensure_isoformat("unexpectedtimeformat")
