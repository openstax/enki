from pathlib import Path
from datetime import datetime, timezone
import json

import pytest

from nebu.cli.main import cli
from nebu.models.book_container import BookContainer
from nebu.models.path_resolver import PathResolver
from nebu.utils import re_first_or_default


@pytest.fixture
def src_data(datadir):
    return datadir / "collection_for_git_workflow"


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


def test_parse_repo(assert_match, invoker, src_data):
    # GIVEN: A valid repository without any tags (or a mock of one)

    # WHEN: pre-assemble is called with a ref
    args = ["parse-repo", str(src_data)]
    result = invoker(cli, args)

    # THEN:
    #   The exit code is 0 (success)
    #   We get the expected output
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.output)
    books_xml = src_data / "META-INF" / "books.xml"
    container = BookContainer.from_str(books_xml.read_bytes(), str(src_data))
    path_resolver = PathResolver(
        container,
        lambda container: Path(container.pages_root).glob("**/*.cnxml"),
        lambda s: re_first_or_default(r"m[0-9]+", s),
    )
    parsed_container = parsed["container"]
    assert parsed_container["books_root"] == getattr(container, "books_root")
    assert parsed_container["pages_root"] == getattr(container, "pages_root")
    assert parsed_container["media_root"] == getattr(container, "media_root")
    assert parsed_container["private_root"] == getattr(
        container, "private_root"
    )
    assert parsed_container["public_root"] == getattr(container, "public_root")
    assert sorted(parsed["modules"].items()) == sorted(
        path_resolver.module_paths_by_id.items()
    )

    assert sorted(parsed["collections"].items()) == sorted(
        path_resolver.collection_paths_by_book.items()
    )
