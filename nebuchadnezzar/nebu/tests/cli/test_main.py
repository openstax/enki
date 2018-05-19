# -*- coding: utf-8 -*-
import io
import zipfile
from cgi import parse_multipart
from copy import deepcopy
from functools import partial
from os import scandir
from pathlib import Path

import pretend
import pytest
import requests_mock

from nebu.cli.main import (
    get_base_url,
    UnknownEnvironment,
)

# This is the response that would come out of Press given
# the data in data/collection.
COLLECTION_PUBLISH_PRESS_RESP_DATA = [
    {'id': 'col11405',
     'version': '1.3',
     'source_id': 'col11405',
     'url': 'https://cnx.org/content/col11405/1.3',
     },
    {'id': 'm37154',
     'version': '1.3',
     'source_id': 'm37154',
     'url': 'https://cnx.org/content/m37154/1.3',
     },
    {'id': 'm37217',
     'version': '1.3',
     'source_id': 'm37217',
     'url': 'https://cnx.org/content/m37217/1.3',
     },
    {'id': 'm37386',
     'version': '1.3',
     'source_id': 'm37386',
     'url': 'https://cnx.org/content/m37386/1.3',
     },
    {'id': 'm40645',
     'version': '1.3',
     'source_id': 'm40645',
     'url': 'https://cnx.org/content/m40645/1.3',
     },
    {'id': 'm40646',
     'version': '1.3',
     'source_id': 'm40646',
     'url': 'https://cnx.org/content/m40646/1.3',
     },
    {'id': 'm42303',
     'version': '1.3',
     'source_id': 'm42303',
     'url': 'https://cnx.org/content/m42303/1.3',
     },
    {'id': 'm42304',
     'version': '1.3',
     'source_id': 'm42304',
     'url': 'https://cnx.org/content/m42304/1.3',
     },
]

CONFIG_FILEPATH = Path(__file__).parent / 'config.ini'


###
# Helpers
###

def pathlib_walk(dir):
    for e in scandir(str(dir)):
        yield Path(e.path)
        if e.is_dir():
            for ee in pathlib_walk(e.path):
                yield Path(ee)


class ResponseCallback:
    """A response callback to be used with requests_mocker"""

    def __init__(self, json_data):
        self.captured_request = None
        self.data = json_data

    def __call__(self, request, context):
        self.captured_request = request
        context.headers['content-type'] = 'text/json'
        import json
        return json.dumps(self.data)


###
# Fixtures
###

@pytest.fixture(autouse=True)
def monekypatch_config(monkeypatch):
    """Point at the testing configuration file"""
    monkeypatch.setenv('NEB_CONFIG', str(CONFIG_FILEPATH))


@pytest.fixture
def faux_cmd(monkeypatch):
    from nebu.cli import main as module
    cmd_grp = deepcopy(module.cli)

    monkeypatch.setattr(module, 'cli', cmd_grp)

    @cmd_grp.command()
    def test():
        from nebu.logger import logger
        logger.info("InfO")
        logger.debug("dEbUg")
        logger.error("ErrOr")


@pytest.fixture
def invoker():
    """Provides a callable for testing a click enabled function using
    the click.testing.CliRunner

    """
    from click.testing import CliRunner
    runner = CliRunner()
    return runner.invoke


@pytest.fixture
def requests_mocker(request):
    mocker = requests_mock.Mocker()
    mocker.start()
    request.addfinalizer(mocker.stop)
    return mocker


@pytest.fixture
def tmpcwd(tmpdir, monkeypatch):
    monkeypatch.chdir(tmpdir)
    return Path(str(tmpdir))


###
# Tests
###


@pytest.mark.usefixtures('faux_cmd')
def test_main(invoker):
    from nebu.cli.main import cli
    args = ['test']
    result = invoker(cli, args)
    assert result.exit_code == 0

    out = result.output
    assert "dEbUg" not in out
    assert "InfO" in out
    assert "ErrOr" in out


@pytest.mark.usefixtures('faux_cmd')
def test_main_with_verbosity(invoker):
    from nebu.cli.main import cli
    args = ['-v', 'test']
    result = invoker(cli, args)
    assert result.exit_code == 0

    out = result.output
    assert "InfO" in out
    assert "dEbUg" in out
    assert "ErrOr" in out


class TestGetBaseUrl:

    def test_success(self):
        env_name = 'foo'
        url = 'http://foo.com'
        settings = {
            'settings': {'environs': {env_name: {'url': url}}},
        }
        ctx = pretend.stub(obj=settings)
        resulting_url = get_base_url(ctx, env_name)
        assert resulting_url == url

    def test_raises(self):
        env_name = 'foo'
        settings = {
            'settings': {'environs': {}},
        }
        ctx = pretend.stub(obj=settings)
        with pytest.raises(UnknownEnvironment) as exc_info:
            get_base_url(ctx, env_name)
        message = exc_info.value.message
        assert message == "unknown environment '{}'".format(env_name)


def test_for_version(monkeypatch, invoker):
    version = 'X.Y.Z'

    import nebu.cli.main
    monkeypatch.setattr(nebu.cli.main, '__version__', version)

    from nebu.cli.main import cli
    args = ['--version']
    result = invoker(cli, args)
    assert result.exit_code == 0

    expected_output = 'Nebuchadnezzar {}\n'.format(version)
    assert result.output == expected_output


def test_for_list(monkeypatch, invoker):

    from nebu.cli.main import cli
    args = ['list']
    result = invoker(cli, args)
    assert result.exit_code == 0

    expected_output = 'test-env\t https://cnx.org\n'
    assert result.output == expected_output


class TestGetCmd:

    def test(self, datadir, tmpcwd, requests_mocker, invoker):
        col_id = 'col11405'
        col_version = '1.19'
        base_url = 'https://legacy.cnx.org/content/{}'.format(col_id)
        get_version_url = '{}/latest/getVersion'.format(base_url)
        completezip_url = '{}/{}/complete'.format(base_url, col_version)

        # Register the getVersion request
        requests_mocker.get(get_version_url, text=col_version)

        # Register the completezip request
        complete_zip = datadir / 'complete.zip'
        content_size = complete_zip.stat().st_size
        with complete_zip.open('rb') as fb:
            headers = {'Content-Length': str(content_size)}
            requests_mocker.get(
                completezip_url,
                content=fb.read(),
                headers=headers,
            )

        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id]
        result = invoker(cli, args)

        assert result.exit_code == 0

        dir = tmpcwd / col_id
        expected = datadir / 'collection'

        def _rel(p, b):
            return p.relative_to(b)

        relative_dir = map(partial(_rel, b=dir), pathlib_walk(dir))
        relative_expected = map(partial(_rel, b=expected),
                                pathlib_walk(expected))
        assert sorted(relative_dir) == sorted(relative_expected)

    def test_with_existing_output_dir(self, tmpcwd, capsys, invoker):
        col_id = 'col00000'

        (tmpcwd / col_id).mkdir()

        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id]
        result = invoker(cli, args)

        assert result.exit_code == 3

        assert 'directory already exists:' in result.output

    def test_failed_request_using_latest(self, requests_mocker, invoker):
        col_id = 'col00000'
        base_url = 'https://legacy.cnx.org/content/{}'.format(col_id)
        get_version_url = '{}/latest/getVersion'.format(base_url)

        requests_mocker.register_uri('GET', get_version_url, status_code=404)

        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id]
        result = invoker(cli, args)

        assert result.exit_code == 4

        msg = "content unavailable for '{}/latest'".format(col_id)
        assert msg in result.output

    def test_failed_request_using_version(self, requests_mocker, invoker):
        col_id = 'col00000'
        col_version = '1.19'
        base_url = 'https://legacy.cnx.org/content/{}'.format(col_id)
        completezip_url = '{}/{}/complete'.format(base_url, col_version)

        requests_mocker.get(completezip_url, status_code=404)

        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id, col_version]
        result = invoker(cli, args)

        assert result.exit_code == 4

        msg = "content unavailable for '{}/{}'".format(col_id, col_version)
        assert msg in result.output

    def test_unavailable_completezip(self, requests_mocker, invoker):
        # This case is possible when the content exists, but the completezip
        # has not been produced.
        col_id = 'col00000'
        col_version = '1.19'
        base_url = 'https://legacy.cnx.org/content/{}'.format(col_id)
        get_version_url = '{}/latest/getVersion'.format(base_url)
        completezip_url = '{}/{}/complete'.format(base_url, col_version)

        # Register the getVersion request
        requests_mocker.get(get_version_url, text=col_version)

        requests_mocker.get(completezip_url, status_code=204)

        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id]
        result = invoker(cli, args)

        assert result.exit_code == 4

        msg = "The content exists, but the completezip is missing"
        assert msg in result.output

        msg = "content unavailable for '{}/{}'".format(col_id, col_version)
        assert msg in result.output


class TestValidateCmd:

    def test_in_cwd(self, datadir, monkeypatch, invoker):
        id = 'collection'
        monkeypatch.chdir(str(datadir / id))

        from nebu.cli.main import cli
        args = ['validate']  # using Current Working Directory (CWD)
        result = invoker(cli, args)

        assert result.exit_code == 0
        assert result.output == 'All good! :)\n'

    def test_outside_cwd(self, datadir, invoker):
        path = datadir / 'collection'

        from nebu.cli.main import cli
        args = ['validate', str(path)]
        result = invoker(cli, args)

        assert result.exit_code == 0
        assert result.output == 'All good! :)\n'

    def test_with_invalid_content(self, datadir, monkeypatch, invoker):
        id = 'invalid_collection'
        monkeypatch.chdir(str(datadir / id))

        from nebu.cli.main import cli
        args = ['validate']  # using Current Working Directory (CWD)
        result = invoker(cli, args)

        assert result.exit_code == 0

        expected_output = (
            ('collection.xml:114:13 -- error: element "para" from '
             'namespace "http://cnx.rice.edu/cnxml" not allowed in '
             'this context'),
            'mux:mux is not a valid identifier',
            ('mux/index.cnxml:61:10 -- error: unknown element "foo" from '
             'namespace "http://cnx.rice.edu/cnxml"'),
        )
        for line in expected_output:
            assert line in result.output

        assert "We've got problems... :(" in result.output


class TestPublishCmd:

    def test_in_cwd(self, datadir, monkeypatch, requests_mocker, invoker):
        id = 'collection'
        publisher = 'CollegeStax'
        message = 'mEssAgE'
        monkeypatch.chdir(str(datadir / id))
        monkeypatch.setenv('XXX_PUBLISHER', publisher)

        # Mock the publishing request
        url = 'https://cnx.org/api/publish-litezip'
        resp_callback = ResponseCallback(COLLECTION_PUBLISH_PRESS_RESP_DATA)
        requests_mocker.register_uri('POST', url, status_code=200,
                                     text=resp_callback)

        from nebu.cli.main import cli
        # Use Current Working Directory (CWD)
        args = ['publish', 'test-env', '.', message]
        result = invoker(cli, args)

        # Check the results
        if result.exception:
            raise result.exception
        assert result.exit_code == 0
        expected_output = (
            'Great work!!! =D\n'
        )
        # FIXME Ignoring temporary formatting of output, just check for
        #       the last line so we know we got to the correct place.
        # assert result.output == expected_output
        assert expected_output in result.output

        # Check the sent contents
        request_data = resp_callback.captured_request._request.body
        # Discover the multipart/form-data boundry
        boundary = request_data.split(b'\r\n')[0][2:]
        form = parse_multipart(io.BytesIO(request_data),
                               {'boundary': boundary})
        assert form['publisher'][0] == publisher.encode('utf8')
        assert form['message'][0] == message.encode('utf8')
        # Check the zipfile for contents
        with zipfile.ZipFile(io.BytesIO(form['file'][0])) as zb:
            included_files = set(zb.namelist())
        expected_files = set((
            'col11405/collection.xml',
            'col11405/m37154/index.cnxml',
            'col11405/m37217/index.cnxml',
            'col11405/m37386/index.cnxml',
            'col11405/m40645/index.cnxml',
            'col11405/m40646/index.cnxml',
            'col11405/m42303/index.cnxml',
            'col11405/m42304/index.cnxml',
        ))
        assert included_files == expected_files

    def test_outside_cwd(self, datadir, monkeypatch,
                         requests_mocker, invoker):
        id = 'collection'
        publisher = 'CollegeStax'
        message = 'mEssAgE'
        monkeypatch.setenv('XXX_PUBLISHER', publisher)

        # Mock the publishing request
        url = 'https://cnx.org/api/publish-litezip'
        resp_callback = ResponseCallback(COLLECTION_PUBLISH_PRESS_RESP_DATA)
        requests_mocker.register_uri('POST', url, status_code=200,
                                     text=resp_callback)

        from nebu.cli.main import cli
        # Use Current Working Directory (CWD)
        args = ['publish', 'test-env', str(datadir / id), message]
        result = invoker(cli, args)

        # Check the results
        if result.exception:
            raise result.exception
        assert result.exit_code == 0
        expected_output = (
            'Great work!!! =D\n'
        )
        # FIXME Ignoring temporary formatting of output, just check for
        #       the last line so we know we got to the correct place.
        # assert result.output == expected_output
        assert expected_output in result.output

        # Check the sent contents
        request_data = resp_callback.captured_request._request.body
        # Discover the multipart/form-data boundry
        boundary = request_data.split(b'\r\n')[0][2:]
        form = parse_multipart(io.BytesIO(request_data),
                               {'boundary': boundary})
        assert form['publisher'][0] == publisher.encode('utf8')
        assert form['message'][0] == message.encode('utf8')
        # Check the zipfile for contents
        with zipfile.ZipFile(io.BytesIO(form['file'][0])) as zb:
            included_files = set(zb.namelist())
        expected_files = set((
            'col11405/collection.xml',
            'col11405/m37154/index.cnxml',
            'col11405/m37217/index.cnxml',
            'col11405/m37386/index.cnxml',
            'col11405/m40645/index.cnxml',
            'col11405/m40646/index.cnxml',
            'col11405/m42303/index.cnxml',
            'col11405/m42304/index.cnxml',
        ))
        assert included_files == expected_files

    def test_with_invalid_content(self, datadir, monkeypatch,
                                  requests_mocker, invoker):
        id = 'invalid_collection'
        publisher = 'CollegeStax'
        message = 'mEssAgE'
        monkeypatch.setenv('XXX_PUBLISHER', publisher)

        from nebu.cli.main import cli
        # Use Current Working Directory (CWD)
        args = ['publish', 'test-env', str(datadir / id), message]
        result = invoker(cli, args)

        # Check the results
        if result.exception and not isinstance(result.exception, SystemExit):
            raise result.exception
        assert result.exit_code == 1
        # Check for the expected failure marker message.
        expected_output = (
            "We've got problems... :(\n"
        )
        assert expected_output in result.output

    def test_with_errors(self, datadir, monkeypatch,
                         requests_mocker, invoker):
        id = 'collection'
        publisher = 'CollegeStax'
        message = 'mEssAgE'
        monkeypatch.setenv('XXX_PUBLISHER', publisher)

        # Mock the publishing request
        url = 'https://cnx.org/api/publish-litezip'
        requests_mocker.register_uri('POST', url, status_code=400,
                                     text='400')

        from nebu.cli.main import cli
        # Use Current Working Directory (CWD)
        args = ['publish', 'test-env', str(datadir / id), message]
        result = invoker(cli, args)

        # Check the results
        if result.exception and not isinstance(result.exception, SystemExit):
            raise result.exception
        assert result.exit_code == 1
        # Check for the expected failure output.
        assert 'ERROR: ' in result.output
        expected_output = (
            'Stop the Press!!! =()\n'
        )
        # FIXME Ignoring temporary formatting of output, just check for
        #       the last line so we know we got to the correct place.
        # assert result.output == expected_output
        assert expected_output in result.output


class TestConfigAtomCmd:

    @pytest.fixture(autouse=True)
    def setup(self, tmpdir, monkeypatch):
        import pkg_resources
        self.resource_filename = 'foo/bar.rng'
        monkeypatch.setattr(pkg_resources, 'resource_filename',
                            lambda *a: self.resource_filename)
        self.tmpdir = Path(str(tmpdir))
        monkeypatch.setattr(Path, 'home', lambda: self.tmpdir)

    def check(self, result):
        assert result.exit_code == 0
        assert 'Wrote ' in result.output
        assert '/.atom/config.cson' in result.output

        filepath = self.tmpdir / '.atom/config.cson'
        with filepath.open('r') as fb:
            assert self.resource_filename in fb.read()

    def test(self, invoker):
        from nebu.cli.main import cli
        args = ['config-atom', '--yes']
        result = invoker(cli, args)
        self.check(result)

    def test_with_exiting_config(self, monkeypatch, invoker):
        filepath = self.tmpdir / '.atom/config.cson'
        backup_filepath = filepath.parent / (filepath.name + '.bak')
        filepath.parent.mkdir()
        with filepath.open('w') as fb:
            fb.write('baz')

        from nebu.cli.main import cli
        args = ['config-atom', '--yes']
        result = invoker(cli, args)
        self.check(result)

        # Check for backup file creation
        assert 'Wrote backup to ' in result.output
        with backup_filepath.open('r') as fb:
            assert 'baz' in fb.read()

    def test_with_exiting_config_and_backup(self, monkeypatch, invoker):
        filepath = self.tmpdir / '.atom/config.cson'
        backup_filepath = filepath.parent / (filepath.name + '.bak')
        filepath.parent.mkdir()
        with filepath.open('w') as fb:
            fb.write('baz')
        with backup_filepath.open('w') as fb:
            fb.write('raz')

        from nebu.cli.main import cli
        args = ['config-atom', '--yes']
        result = invoker(cli, args)
        self.check(result)

        # Check for backup file is overwritten
        assert 'Wrote backup to ' in result.output
        with backup_filepath.open('r') as fb:
            assert 'baz' in fb.read()
