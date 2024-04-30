import json
from pathlib import Path
from collections import defaultdict
from typing import cast

from lxml import etree
import pytest

from nebu.cli import assemble
from nebu.cli.main import cli
from nebu.models.path_resolver import PathResolver


@pytest.fixture
def shutil_stub(monkeypatch, create_stub):
    class ShutilStub:
        move = create_stub()

    monkeypatch.setattr(assemble, "shutil", ShutilStub)
    return ShutilStub


@pytest.fixture
def save_resource_metadata_stub(monkeypatch, create_stub):
    stub = create_stub()
    monkeypatch.setattr(assemble, "save_resource_metadata", stub)
    return stub


@pytest.fixture
def result_data(datadir):
    return datadir / "assembled_collection_for_bakedpdf_workflow"


@pytest.fixture
def edit_collection_xml(request):
    def _edit_collection_xml(filepath):
        filepath.rename(filepath.parent / "collection.xml.bak")
        with (filepath.parent / "collection.xml.bak").open("r") as f:
            root = etree.parse(f)

        content = root.find("{http://cnx.rice.edu/collxml}content")
        # remove the first module of the first subcollection
        sc1 = content.find("{http://cnx.rice.edu/collxml}subcollection")
        m1 = sc1.xpath(
            ".//col:module", namespaces={"col": "http://cnx.rice.edu/collxml"}
        )[0]
        m1.getparent().remove(m1)
        with filepath.open("wb") as f:
            f.write(etree.tostring(root))

        def restore_collection_xml():
            (filepath.parent / "collection.xml.bak").replace(filepath)

        request.addfinalizer(restore_collection_xml)

    return _edit_collection_xml


@pytest.fixture
def add_exercises(request):
    def _add_exercises(filepath):
        bakpath = filepath.parent / "{}.bak".format(filepath.name)
        filepath.rename(bakpath)

        with bakpath.open("r") as f:
            content = f.read()

        # add an exercise to the first para
        with filepath.open("w") as f:
            f.write(
                content.replace(
                    "</para>",
                    "</para>"
                    '<para id="exercise-1">'
                    '<link class="os-embed" url="#ost/api/ex/k12phys-ch01-ex008"/>'
                    "</para>"
                    '<para id="exercise-2">'
                    '<link class="os-embed" url="#exercise/Ch01-CI-Intro-RQ01"/>'
                    "</para>",
                    1,
                )
            )

        def restore_file():
            bakpath.replace(filepath)

        request.addfinalizer(restore_file)

    return _add_exercises


class TestAssembleCmd:
    @pytest.fixture(autouse=True)
    def stub_SingleHTMLFormatter(self, monkeypatch):
        def fake_collection_to_assembled_xhtml(*_args, **_kwargs):
            return b"faux"

        self.collection_to_assembled_xhtml = fake_collection_to_assembled_xhtml
        monkeypatch.setattr(
            assemble,
            "collection_to_assembled_xhtml",
            self.collection_to_assembled_xhtml,
        )

    def test(self, tmp_path, git_collection_data, result_data, invoker):
        output_dir = tmp_path / "build"

        args = [
            "assemble",  # (target)
            str(git_collection_data),
            str(output_dir),
            str(tmp_path),
        ]
        result = invoker(cli, args)

        output_file = (output_dir / "collection.assembled.xhtml").resolve()

        # Verify the invocation output
        assert result.exit_code == 0, result.output

        # Verify the file output
        with output_file.open("rb") as ofb:
            assert ofb.read().decode() == "faux"

    def test_output_dir_exists(self, tmp_path, git_collection_data, invoker):
        output_dir = tmp_path / "build"
        output_dir.mkdir()

        from nebu.cli.main import cli

        args = [
            "assemble",  # (target)
            str(git_collection_data),
            str(output_dir),
            str(tmp_path),
        ]
        result = invoker(cli, args)

        # Verify the invocation output
        assert result.exit_code == 0, result.output

    def test_edited_collection_xml(
        self,
        tmp_path,
        git_collection_data,
        invoker,
        edit_collection_xml,
        git_path_resolver
    ):
        output_dir = tmp_path / "build"
        output_dir.mkdir()

        edit_collection_xml(
            Path(git_path_resolver.get_collection_path("collection"))
        )

        from nebu.cli.main import cli

        args = ["assemble", str(git_collection_data), str(output_dir), str(tmp_path)]
        result = invoker(cli, args)

        assert result.exit_code == 0

        # the first module in the first subcollection was removed
        assert not (
            output_dir / "d93df8ff-6e4a-4a5e-befc-ba5a144f309c"
        ).is_symlink()


@pytest.fixture
def exercise_mock(datadir, requests_mock):
    with (datadir / "exercise_w_tag.json").open("r") as f:
        requests_mock.get(
            "https://exercises.openstax.org/api/exercises?"
            "q=tag:k12phys-ch01-ex008",
            json=json.load(f),
        )

    with (datadir / "exercise_w_nickname.json").open("r") as f:
        requests_mock.get(
            "https://exercises.openstax.org/api/exercises?"
            "q=nickname:Ch01-CI-Intro-RQ01",
            json=json.load(f),
        )


class TestAssembleIntegration:
    def test_exercises(
        self,
        tmp_path,
        git_collection_data,
        add_exercises,
        exercise_mock,
        invoker,
        git_path_resolver,
        shutil_stub,
        save_resource_metadata_stub,
    ):
        output_dir = tmp_path / "build"
        output_dir.mkdir()

        add_exercises(Path(git_path_resolver.get_module_path("m46882")))

        from nebu.cli.main import cli

        args = (
            "assemble",
            "--exercise-host",
            "exercises.openstax.org",
            str(git_collection_data),
            str(output_dir),
            str(tmp_path),
        )
        result = invoker(cli, args)

        assert result.exit_code == 0, result.exception

        # Find the exercises in the assembled html
        with (output_dir / "collection.assembled.xhtml").open("r") as f:
            html = f.read()

        assert "Which statement best compares and contrasts" in html
        assert "To gain scientific knowledge" in html


@pytest.fixture
def current_snapshot_dir(snapshot_dir):
    return snapshot_dir / "assembled"


@pytest.fixture
def assembled_pair(
    parts_tuple,
    exercise_mock,
    git_path_resolver,
    shutil_stub,
    save_resource_metadata_stub,
):
    from nebu.cli.assemble import collection_to_assembled_xhtml

    media_handler = assemble.media_handler_factory(
        "fake-resources",
        {}
    )

    collection, docs_by_id, docs_by_uuid = parts_tuple
    assembled_collection = collection_to_assembled_xhtml(
        collection,
        docs_by_id,
        docs_by_uuid,
        git_path_resolver,
        None,
        "exercises.openstax.org",
        media_handler,
    )
    return (collection, assembled_collection)


# Check documents, cols, etc. after all mutations were applied
def test_doc_to_html(assert_match, assembled_pair):
    from nebu.formatters import _doc_to_html

    collection, _ = assembled_pair

    docs_by_id = {doc.metadata["id"]: doc for doc in collection.documents}

    for doc_id, document in docs_by_id.items():
        assert_match(_doc_to_html(document), doc_id + ".xhtml")


def test_save_resource_metadata(tmp_path):
    # Mostly just checking that the name is correct
    name = "123"
    expected = tmp_path / f"{name}.json"
    assemble.save_resource_metadata(
        {"some": "thing"},
        tmp_path,
        name
    )
    assert expected.exists()
    assert expected.read_text() == '{"some": "thing"}'


def test_col_to_html(assert_match, assembled_pair):
    from nebu.models.book_part import PartType
    from nebu.formatters import _col_to_html

    collection, _ = assembled_pair

    assert_match(_col_to_html(collection), "collection.xhtml")
    for i, subcol in enumerate(collection.get_parts_by_type(PartType.SUBCOL)):
        assert_match(_col_to_html(subcol), f"subcol-{i}.xhtml")


def test_h5p_media_handler(
    create_stub,
    shutil_stub,
    save_resource_metadata_stub,
    monkeypatch,
):
    fake_path = "fake-path"
    resource_dir = "resources"
    filename = "sha1"
    metadata = {}

    class PathResolverStub:
        find_interactives_paths = create_stub().returns({
            "public": fake_path,
        })

    class ElementStub:
        attrib = defaultdict(lambda: fake_path)

    metadata_stub = create_stub().returns((filename, metadata))
    monkeypatch.setattr(assemble, "get_media_metadata", metadata_stub)
    media_handler = assemble.h5p_media_handler_factory(
        cast(PathResolver, PathResolverStub()),
        assemble.media_handler_factory(resource_dir)
    )
    element_stub = ElementStub()
    media_handler("test", element_stub, "src", True)
    assert len(shutil_stub.move.calls) > 0
    # Should use path returned by path resolver
    expected_src_path = fake_path
    # Should use name returned by get_media_metadata (sha1)
    expected_dst_path = str(Path(resource_dir) / filename)
    assert shutil_stub.move.calls[0]["args"] == (
        expected_src_path, expected_dst_path
    )
    # Should set attribute and the new one should include the name
    assert filename in element_stub.attrib["src"]
    # Should save metadata
    assert len(save_resource_metadata_stub.calls) > 0


def test_assemble_collection(
    assert_match,
    assembled_pair,
    shutil_stub,
    save_resource_metadata_stub,
):
    _, assembled_collection = assembled_pair
    assert_match(
        assembled_collection.decode(), "collection.assembled.xhtml"
    )
    # Ensure media files included in the integration test
    assert len(shutil_stub.move.calls) > 0
    assert len(save_resource_metadata_stub.calls) > 0
