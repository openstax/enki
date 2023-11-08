from pathlib import Path
from shutil import copytree, rmtree
from datetime import datetime, timezone
import json
from itertools import chain

import pytest

from nebu.cli.main import cli
from nebu.models.book_container import BookContainer
from nebu.models.path_resolver import PathResolver
from nebu.utils import re_first_or_default
from nebu.xml_utils import open_xml
from nebu.parse import NSMAP as CNXML_NSMAP


MOCK_TAG_NAME = "my-mock-tag"
MD_MODULE = 0
MD_COLLECTION = 1


@pytest.fixture
def src_data(datadir):
    return datadir / "collection_for_git_workflow"


@pytest.fixture
def tmp_book_dir(src_data, tmp_path):
    output_dir = Path(tmp_path) / "pre-assemble"
    copytree(src_data, output_dir)
    # Remove existing metadata from this copy of the test data
    # This metadata is required for other tests, but it causes problems here
    for f in chain(*map(output_dir.glob, ("**/*.cnxml", "**/*.xml"))):
        tree = open_xml(f)
        metadata = tree.xpath('//*[local-name() = "metadata"]')
        if len(metadata) == 0:
            continue
        metadata_el = metadata[0]
        for el in metadata_el.xpath(
            "//md:revised | //md:version | //md:canonical-book-uuid",
            namespaces=CNXML_NSMAP,
        ):
            metadata_el.remove(el)
        with open(f, "wb") as fout:
            tree.write(fout, encoding="utf-8", xml_declaration=False)
    return output_dir


@pytest.fixture
def current_snapshot_dir(snapshot_dir):
    return snapshot_dir / "pre-assemble"


@pytest.fixture
def repo_mock(mocker):
    repo_mock = mocker.MagicMock()
    commit_mock = repo_mock().head.commit
    commit_mock.committed_datetime = datetime.fromtimestamp(
        0.0, tz=timezone.utc
    )
    commit_mock.hexsha = "0000000"
    return repo_mock


def parse_metadata(book_dir):
    books_xml = book_dir / "META-INF" / "books.xml"

    container = BookContainer.from_str(books_xml.read_bytes(), str(book_dir))
    path_resolver = PathResolver(
        container,
        lambda container: Path(container.pages_root).glob("**/*.cnxml"),
        lambda s: re_first_or_default(r"m[0-9]+", s),
    )

    for thing_type, resolver_dict, selector in (
        (
            MD_MODULE,
            path_resolver.module_paths_by_id,
            "//md:revised | //md:canonical-book-uuid",
        ),
        (
            MD_COLLECTION,
            path_resolver.collection_paths_by_book,
            "//md:revised | //md:version",
        ),
    ):
        for thing_id, path in resolver_dict.items():
            tree = open_xml(path)
            metadata = tree.xpath(selector, namespaces=CNXML_NSMAP)
            yield (
                thing_type,
                [
                    {"tag": el.tag, "line": el.sourceline, "text": el.text}
                    for el in metadata
                ],
                thing_id,
            )


def test_pre_assemble_cmd_no_tags(
    repo_mock, mocker, assert_match, invoker, tmp_book_dir
):
    # GIVEN: A valid repository without any tags (or a mock of one)

    # WHEN: pre-assemble is called with a ref
    args = ["pre-assemble", str(tmp_book_dir), "main"]
    mocker.patch("nebu.cli.pre_assemble.Repo", repo_mock)
    result = invoker(cli, args)

    # THEN:
    #   The exit code is 0 (success)
    #   Modules contained in a collection are updated with git metadata
    #   Modules not contained in a collection are left alone (m50000)
    #   The commit sha is used
    assert result.exit_code == 0, result.output
    for thing_type, metadata, thing_id in parse_metadata(tmp_book_dir):
        assert_match(
            json.dumps(metadata, indent=2),
            f"{thing_id}-metadata.json",
            use_func_name=thing_type != MD_MODULE,
        )

    rmtree(tmp_book_dir)


@pytest.mark.parametrize("git_ref", ("main", MOCK_TAG_NAME))
def test_pre_assemble_cmd_with_tags(
    mocker,
    assert_match,
    invoker,
    tmp_book_dir,
    repo_mock,
    git_ref,
):
    # GIVEN: Exactly one tag that points to the same commit as main
    commit_mock = repo_mock().head.commit
    tag_mock = mocker.MagicMock()
    tag_mock.name = MOCK_TAG_NAME
    tag_mock.commit = commit_mock
    repo_mock().tags = [tag_mock]

    # WHEN: pre-assemble is called with a git ref that is tagged in the
    #       repository.
    args = ["pre-assemble", str(tmp_book_dir), git_ref]
    mocker.patch("nebu.cli.pre_assemble.Repo", repo_mock)
    result = invoker(cli, args)

    # THEN:
    #   The exit code is 0 (success)
    #   The module metadata remains unchanged
    #   The tag name is used instead of the commit sha
    assert result.exit_code == 0, result.output
    for thing_type, metadata, thing_id in parse_metadata(tmp_book_dir):
        assert_match(
            json.dumps(metadata, indent=2),
            f"{thing_id}-metadata.json",
            use_func_name=thing_type != MD_MODULE,
        )

    rmtree(tmp_book_dir)
