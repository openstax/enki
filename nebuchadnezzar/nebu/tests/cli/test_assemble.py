from pathlib import Path

from lxml import etree
import pytest

from nebu.cli import assemble
from nebu.cli.main import cli


@pytest.fixture
def src_data(datadir):
    return datadir / 'collection_for_bakedpdf_workflow'


@pytest.fixture
def result_data(datadir):
    return datadir / 'assembled_collection_for_bakedpdf_workflow'


@pytest.fixture
def edit_collection_xml(request):
    def _edit_collection_xml(filepath):
        filepath.rename(filepath.parent / 'collection.xml.bak')
        with (filepath.parent / 'collection.xml.bak').open('r') as f:
            root = etree.parse(f)

        content = root.find('{http://cnx.rice.edu/collxml}content')
        # remove the first module of the first subcollection
        sc1 = content.find('{http://cnx.rice.edu/collxml}subcollection')
        m1 = sc1.xpath('.//col:module',
                       namespaces={'col': 'http://cnx.rice.edu/collxml'})[0]
        m1.getparent().remove(m1)
        with filepath.open('wb') as f:
            f.write(etree.tostring(root))

        def restore_collection_xml():
            (filepath.parent / 'collection.xml.bak').replace(filepath)

        request.addfinalizer(restore_collection_xml)

    return _edit_collection_xml


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

    def test_edited_collection_xml(self, tmp_path, src_data, invoker,
                                   edit_collection_xml):
        output_dir = tmp_path / 'build'
        output_dir.mkdir()

        edit_collection_xml(src_data / 'collection.xml')

        from nebu.cli.main import cli
        args = ['assemble', str(src_data), str(output_dir)]
        result = invoker(cli, args)

        assert result.exit_code == 0

        # the first module in the first subcollection was removed
        assert not (output_dir / 'm46913').is_symlink()
        # the second module in the first subcollection should be there
        assert (output_dir / 'm46909').is_symlink()
