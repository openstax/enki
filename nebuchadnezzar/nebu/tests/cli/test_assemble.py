import json

from lxml import etree
import pytest
from pathlib import Path

from nebu.cli import assemble
from nebu.cli.main import cli


@pytest.fixture
def src_data(datadir):
    return datadir / "collection_for_git_workflow"


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

    def test(self, tmp_path, src_data, result_data, invoker):
        output_dir = tmp_path / "build"

        args = [
            "assemble",  # (target)
            str(src_data),
            str(output_dir),
        ]
        result = invoker(cli, args)

        output_file = (output_dir / "collection.assembled.xhtml").resolve()

        # Verify the invocation output
        assert result.exit_code == 0, result.output

        # Verify the file output
        with output_file.open("rb") as ofb:
            assert ofb.read().decode() == "faux"

    def test_output_dir_exists(self, tmp_path, src_data, invoker):
        output_dir = tmp_path / "build"
        output_dir.mkdir()

        from nebu.cli.main import cli

        args = [
            "assemble",  # (target)
            str(src_data),
            str(output_dir),
        ]
        result = invoker(cli, args)

        # Verify the invocation output
        assert result.exit_code == 0, result.output

    def test_edited_collection_xml(
        self,
        tmp_path,
        src_data,
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

        args = ["assemble", str(src_data), str(output_dir)]
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
        src_data,
        add_exercises,
        exercise_mock,
        invoker,
        git_path_resolver
    ):
        output_dir = tmp_path / "build"
        output_dir.mkdir()

        add_exercises(Path(git_path_resolver.get_module_path("m46882")))

        from nebu.cli.main import cli

        args = (
            "assemble",
            "--exercise-host",
            "exercises.openstax.org",
            str(src_data),
            str(output_dir),
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
def assembled_pair(parts_tuple, exercise_mock, git_path_resolver):
    from nebu.cli.assemble import collection_to_assembled_xhtml

    collection, docs_by_id, docs_by_uuid = parts_tuple
    assembled_collection = collection_to_assembled_xhtml(
        collection,
        docs_by_id,
        docs_by_uuid,
        git_path_resolver,
        None,
        "exercises.openstax.org"
    )
    return (collection, assembled_collection)


# Check documents, cols, etc. after all mutations were applied
def test_doc_to_html(assert_match, assembled_pair):
    from nebu.formatters import _doc_to_html

    collection, _ = assembled_pair

    docs_by_id = {doc.metadata["id"]: doc for doc in collection.documents}

    for doc_id, document in docs_by_id.items():
        assert_match(_doc_to_html(document), doc_id + ".xhtml")


def test_col_to_html(assert_match, assembled_pair):
    from nebu.models.book_part import PartType
    from nebu.formatters import _col_to_html

    collection, _ = assembled_pair

    assert_match(_col_to_html(collection), "collection.xhtml")
    for i, subcol in enumerate(collection.get_parts_by_type(PartType.SUBCOL)):
        assert_match(_col_to_html(subcol), f"subcol-{i}.xhtml")


def test_assemble_collection(
    assert_match, assembled_pair
):
    _, assembled_collection = assembled_pair
    assert_match(
        assembled_collection.decode(), "collection.assembled.xhtml"
    )
