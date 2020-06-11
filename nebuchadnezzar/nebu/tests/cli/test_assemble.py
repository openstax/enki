from pathlib import Path
import json

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


@pytest.fixture
def add_exercises(request):
    def _add_exercises(filepath):
        bakpath = filepath.parent / '{}.bak'.format(filepath.name)
        filepath.rename(bakpath)

        with bakpath.open('r') as f:
            content = f.read()

        # add an exercise to the first para
        with filepath.open('w') as f:
            f.write(content.replace(
                '</para>',
                '</para>'
                '<para id="exercise-1">'
                '<link class="os-embed" url="#ost/api/ex/k12phys-ch01-ex008"/>'
                '</para>'
                '<para id="exercise-2">'
                '<link class="os-embed" url="#exercise/Ch01-CI-Intro-RQ01"/>'
                '</para>',
                1))

        def restore_file():
            bakpath.replace(filepath)

        request.addfinalizer(restore_file)

    return _add_exercises


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
        m46882_dir = (output_dir / '3fb20c92-9515-420b-ab5e-6de221b89e99')
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
        (output_dir / '3fb20c92-9515-420b-ab5e-6de221b89e99').\
            symlink_to(output_dir)
        (output_dir / '3fb20c92-9515-420b-ab5e-6de221b89e99.xhtml').touch()

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

        assert (output_dir / '3fb20c92-9515-420b-ab5e-6de221b89e99').\
            is_symlink()
        expected_filepath = (src_data / 'm46882')
        output_filepath = \
            Path(str(output_dir / '3fb20c92-9515-420b-ab5e-6de221b89e99'))
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
        assert not (output_dir / 'd93df8ff-6e4a-4a5e-befc-ba5a144f309c').\
            is_symlink()
        # the second module in the first subcollection should be there
        assert (output_dir / 'cb418599-f69b-46c1-b0ef-60d9e36e677f').\
            is_symlink()


class TestAssembleIntegration:
    def test_exercises(self, tmp_path, src_data, add_exercises, requests_mock,
                       invoker, datadir):
        output_dir = tmp_path / 'build'
        output_dir.mkdir()

        add_exercises(src_data / 'm46882' / 'index.cnxml')

        with (datadir / 'exercise_w_tag.json').open('r') as f:
            requests_mock.get(
                'https://exercises.cnx.org/api/exercises?'
                'q=tag:k12phys-ch01-ex008',
                json=json.load(f))

        with (datadir / 'exercise_w_nickname.json').open('r') as f:
            requests_mock.get(
                'https://exercises.cnx.org/api/exercises?'
                'q=nickname:Ch01-CI-Intro-RQ01',
                json=json.load(f))

        from nebu.cli.main import cli
        args = ('assemble', '--exercise-host', 'exercises.cnx.org',
                str(src_data), str(output_dir))
        result = invoker(cli, args)

        assert result.exit_code == 0, result.exception

        # Find the exercises in the assembled html
        with (output_dir / 'collection.assembled.xhtml').open('r') as f:
            html = f.read()

        assert 'Which statement best compares and contrasts' in html
        assert 'To gain scientific knowledge' in html
