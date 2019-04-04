from unittest import mock

import pytest

from nebu.cli.mathify import INPUT_FILE, OUTPUT_FILE, IMAGE_TAG, REPO_URL


@pytest.fixture
def mathify_cleanup(request, datadir):
    def _mathify_cleanup(filenames=(INPUT_FILE, OUTPUT_FILE)):
        def cleanup():
            for filename in filenames:
                output_file = datadir / filename
                if output_file.is_file():
                    output_file.unlink()

        cleanup()
        request.addfinalizer(cleanup)
    return _mathify_cleanup


def create_collection_xhtml(datadir, filename=INPUT_FILE):
    with (datadir / filename).open('w') as out:
        with (datadir / 'test_collection.xhtml').open('r') as in_:
            out.write(in_.read())


def create_mathified_xhtml(datadir):
    def inner(*args, **kwargs):
        with (datadir / OUTPUT_FILE).open('w') as out:
            out.write('mathified collection xhtml')
        return b''
    return inner


@pytest.fixture
def mathify_docker_client(datadir):
    patcher = mock.patch('nebu.cli.mathify.docker')
    mock_docker = patcher.start()
    client = mock_docker.from_env()
    client.images.pull.return_value = ['<cnx-bakedpdf image>']
    client.containers.run.side_effect = create_mathified_xhtml(
        datadir)
    yield client
    patcher.stop()


class TestMathifyCmd:
    def test_w_collection_xhtml(self, datadir, invoker, mathify_cleanup,
                                mathify_docker_client):
        docker_client = mathify_docker_client
        mathify_cleanup()
        create_collection_xhtml(datadir)

        from nebu.cli.main import cli
        args = ['mathify', str(datadir)]
        result = invoker(cli, args)

        assert docker_client.images.pull.called
        assert not docker_client.images.build.called
        assert docker_client.containers.run.called
        (image_tag,), kwargs = docker_client.containers.run.call_args
        assert image_tag == IMAGE_TAG
        assert 'node typeset/start' in kwargs['command']

        assert result.exit_code == 0
        assert (datadir / OUTPUT_FILE).is_file()

    def test_w_input_file(self, datadir, invoker, mathify_cleanup,
                          mathify_docker_client):
        docker_client = mathify_docker_client
        mathify_cleanup()
        create_collection_xhtml(datadir, filename='collection.xhtml')

        from nebu.cli.main import cli
        args = ['mathify', '-i', str(datadir / 'collection.xhtml'),
                str(datadir)]
        result = invoker(cli, args)

        assert docker_client.containers.run.called
        kwargs = docker_client.containers.run.call_args[1]
        assert 'collection.xhtml' in kwargs['command']

        assert result.exit_code == 0

    def test_input_file_directory(self, datadir, invoker, mathify_cleanup,
                                  mathify_docker_client, tmp_path):
        docker_client = mathify_docker_client
        mathify_cleanup()

        # Note, the source option's value isn't really important, because
        # the assemble command is mocked.
        source_dir = (tmp_path / 'source')
        source_dir.mkdir()
        workspace = datadir / 'does-not-exist'

        from nebu.cli.main import cli
        args = [
            'mathify',
            '--input-file', str(source_dir),
            str(workspace)]
        result = invoker(cli, args)

        assert result.exit_code == 1
        assert 'Input file {} not found or is not a file.'.format(source_dir) \
            == str(result.exception)
        assert not docker_client.containers.run.called

    def test_input_file_not_found(self, datadir, invoker, mathify_cleanup,
                                  mathify_docker_client, tmp_path):
        mathify_cleanup()

        from nebu.cli.main import cli
        args = ['mathify', '--input-file', str(tmp_path / 'does-not-exist'),
                str(datadir)]
        result = invoker(cli, args)

        assert 'Path "{}" does not exist.'.format(
            tmp_path / 'does-not-exist') in result.output
        assert result.exit_code == 2

    def test_wo_collection_xhtml_or_source(self, datadir, invoker,
                                           mathify_cleanup):
        mathify_cleanup()

        from nebu.cli.main import cli
        args = ['mathify', str(datadir)]
        result = invoker(cli, args)

        assert result.exit_code == 1
        assert 'Input file {} not found or is not a file.'.format(
            datadir / INPUT_FILE) == str(result.exception)

    def test_image_not_found(self, datadir, invoker, mathify_cleanup,
                             mathify_docker_client):
        docker_client = mathify_docker_client
        mathify_cleanup()
        create_collection_xhtml(datadir)
        docker_client.images.list.return_value = []
        docker_client.images.build.side_effect = lambda *args, **kwargs: \
            ('<image>', [{'stream': 'build log'}])

        from nebu.cli.main import cli
        args = ['mathify', str(datadir)]
        result = invoker(cli, args, catch_exceptions=False)
        assert result.exit_code == 0

        assert docker_client.images.build.called
        args, kwargs = docker_client.images.build.call_args
        assert kwargs == {
            'path': REPO_URL,
            'tag': IMAGE_TAG,
            'rm': True,
        }

    def test_build_flag(self, datadir, invoker, mathify_cleanup,
                        mathify_docker_client):
        docker_client = mathify_docker_client
        mathify_cleanup()
        create_collection_xhtml(datadir)
        docker_client.images.build.side_effect = lambda *args, **kwargs: \
            ('<image>', [{'stream': 'build log'}])

        from nebu.cli.main import cli
        args = ['mathify', '--build', str(datadir)]
        result = invoker(cli, args, catch_exceptions=False)
        assert result.exit_code == 0

        assert docker_client.images.build.called
        args, kwargs = docker_client.images.build.call_args
        assert kwargs == {
            'path': REPO_URL,
            'tag': IMAGE_TAG,
            'rm': True,
        }
