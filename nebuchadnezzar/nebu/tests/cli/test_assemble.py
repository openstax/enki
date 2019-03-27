from pathlib import Path

import pytest

from nebu.cli import assemble
from nebu.cli.main import cli


@pytest.fixture
def src_data(datadir):
    return datadir / 'collection_for_bakedpdf_workflow'


@pytest.fixture
def result_data(datadir):
    return datadir / 'assembled_collection_for_bakedpdf_workflow'


class FauxSingleHTMLFormatter(object):
    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    def __bytes__(self):
        return b'faux'


class TestAssembleCmd:

    @pytest.fixture(autouse=True)
    def stub_SingleHTMLFormatter(self, monkeypatch):
        self.SingleHTMLFormatter = FauxSingleHTMLFormatter
        monkeypatch.setattr(
            assemble,
            'SingleHTMLFormatter',
            self.SingleHTMLFormatter,
        )

    def test(self, tmp_path, src_data, result_data, invoker):
        output_dir = tmp_path / 'build'

        args = [
            'assemble',  # (target)
            str(src_data), str(output_dir),
        ]
        result = invoker(cli, args)

        output_file = (output_dir / 'collection.assembled.xhtml').resolve()

        # Verify the invocation output
        assert result.exit_code == 0, result.output

        # Verify the file output
        with output_file.open('rb') as ofb:
            assert ofb.read().decode() == 'faux'

        # Verify symlink to collection.xml
        collection_xml = (output_dir / 'collection.xml')
        assert collection_xml.is_symlink()
        # note, Path wraps this because pathlib2.Path is used
        # see also `_flavour` property on the object, which is used in
        # equality comparison.
        expected_filepath = (src_data / 'collection.xml').resolve()
        assert Path(str(collection_xml.resolve())) == expected_filepath

        # Verify symlink to original data directories
        m46882_dir = (output_dir / 'm46882')
        assert m46882_dir.is_symlink()
        expected_dir = (src_data / 'm46882').resolve()
        assert Path(str(m46882_dir.resolve())) == expected_dir

    def test_output_dir_exists(self, tmp_path, src_data, invoker):
        output_dir = tmp_path / 'build'
        output_dir.mkdir()

        from nebu.cli.main import cli
        args = [
            'assemble',  # (target)
            str(src_data), str(output_dir),
        ]
        result = invoker(cli, args)

        # Verify the invocation output
        assert result.exit_code == 0, result.output

    def test_output_files_exists_proceed(self, tmp_path, src_data, invoker):
        output_dir = tmp_path / 'build'
        output_dir.mkdir()
        (output_dir / 'collection.assembled.xhtml').touch()

        from nebu.cli.main import cli
        args = [
            'assemble',  # (target)
            str(src_data), str(output_dir),
        ]
        # This asks to replace the collection.assembled.xhtml file
        result = invoker(cli, args, input='y\n')  # 'y', proceed with removal

        # Verify the invocation output
        assert result.exit_code == 0, result.output

    def test_output_file_exists_abort(self, tmp_path, src_data, invoker):
        output_dir = tmp_path / 'build'
        output_dir.mkdir()
        (output_dir / 'collection.assembled.xhtml').touch()

        from nebu.cli.main import cli
        args = [
            'assemble',  # (target)
            str(src_data), str(output_dir),
        ]
        result = invoker(cli, args, input='\n')  # accept default: 'N'

        # Verify the invocation output
        assert result.exit_code == 1, result.output
        assert 'Aborted!' in result.output

    def test_supporting_output_files_exist(self, tmp_path, src_data, invoker):
        output_dir = tmp_path / 'build'
        output_dir.mkdir()
        # clearly incorrect, but testable for the correct link
        (output_dir / 'collection.xml').symlink_to(output_dir)
        (output_dir / 'm46882').symlink_to(output_dir)
        (output_dir / 'm46882.xhtml').touch()

        from nebu.cli.main import cli
        args = [
            'assemble',  # (target)
            str(src_data), str(output_dir),
        ]
        result = invoker(cli, args)

        # Verify the invocation output
        assert result.exit_code == 0, result.output

        # Test the links are correct and not the previous existing links
        assert (output_dir / 'collection.xml').is_symlink()
        expected_filepath = (src_data / 'collection.xml')
        output_filepath = Path(str(output_dir / 'collection.xml'))
        assert output_filepath.resolve() == expected_filepath

        assert (output_dir / 'm46882').is_symlink()
        expected_filepath = (src_data / 'm46882')
        output_filepath = Path(str(output_dir / 'm46882'))
        assert output_filepath.resolve() == expected_filepath
