# -*- coding: utf-8 -*-
import io
import zipfile
from cgi import parse_multipart
from copy import deepcopy
from functools import partial
from pathlib import Path
from os import scandir

import pytest
import requests_mock


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


def test_get_cmd(datadir, tmpcwd, requests_mocker, invoker):
    col_id = 'col11405'
    url = 'https://legacy.cnx.org/content/{}/latest/complete'.format(col_id)

    complete_zip = datadir / 'complete.zip'
    content_size = complete_zip.stat().st_size
    with complete_zip.open('rb') as fb:
        headers = {'Content-Length': str(content_size)}
        requests_mocker.get(url, content=fb.read(), headers=headers)

    from nebu.cli.main import cli
    args = ['get', col_id]
    result = invoker(cli, args)

    assert result.exit_code == 0

    dir = tmpcwd / col_id
    expected = datadir / 'collection'

    def _rel(p, b): return p.relative_to(b)

    relative_dir = map(partial(_rel, b=dir), pathlib_walk(dir))
    relative_expected = map(partial(_rel, b=expected), pathlib_walk(expected))
    assert sorted(relative_dir) == sorted(relative_expected)


def test_get_cmd_with_existing_output_dir(tmpcwd, capsys, invoker):
    col_id = 'col00000'

    (tmpcwd / col_id).mkdir()

    from nebu.cli.main import cli
    args = ['get', col_id]
    result = invoker(cli, args)

    assert result.exit_code == 3

    assert 'output directory cannot exist:' in result.output


def test_get_cmd_with_failed_request(requests_mocker, invoker):
    col_id = 'col00000'
    url = 'https://legacy.cnx.org/content/{}/latest/complete'.format(col_id)

    requests_mocker.register_uri('GET', url, status_code=404)

    from nebu.cli.main import cli
    args = ['get', col_id]
    result = invoker(cli, args)

    assert result.exit_code == 4

    msg = "content unavailable for '{}/latest'".format(col_id)
    assert msg in result.output


def test_validate_cmd_in_cwd(datadir, monkeypatch, invoker):
    id = 'collection'
    monkeypatch.chdir(str(datadir / id))

    from nebu.cli.main import cli
    args = ['validate']  # using Current Working Directory (CWD)
    result = invoker(cli, args)

    assert result.exit_code == 0
    assert result.output == 'All good! :)\n'


def test_validate_cmd_outside_cwd(datadir, invoker):
    path = datadir / 'collection'

    from nebu.cli.main import cli
    args = ['validate', str(path)]
    result = invoker(cli, args)

    assert result.exit_code == 0
    assert result.output == 'All good! :)\n'


def test_validate_cmd_with_invalid_content(datadir, monkeypatch, invoker):
    id = 'invalid_collection'
    monkeypatch.chdir(str(datadir / id))

    from nebu.cli.main import cli
    args = ['validate']  # using Current Working Directory (CWD)
    result = invoker(cli, args)

    assert result.exit_code == 0

    expected_output = (
        ('collection.xml:114:13 -- error: element "para" from '
         'namespace "http://cnx.rice.edu/cnxml" not allowed in this context'),
        'mux:mux is not a valid identifier',
        ('mux/index.cnxml:61:10 -- error: unknown element "foo" from '
         'namespace "http://cnx.rice.edu/cnxml"'),
    )
    for line in expected_output:
        assert line in result.output

    assert "We've got problems... :(" in result.output


def test_publish_cmd_in_cwd(datadir, monkeypatch, requests_mocker, invoker):
    id = 'collection'
    publisher = 'CollegeStax'
    message = 'mEssAgE'
    monkeypatch.chdir(str(datadir / id))
    monkeypatch.setenv('XXX_PUBLISHER', publisher)

    # Mock the publishing request
    url = 'https://cnx.org/api/v3/publish'
    resp_callback = ResponseCallback(COLLECTION_PUBLISH_PRESS_RESP_DATA)
    requests_mocker.register_uri('POST', url, status_code=200,
                                 text=resp_callback)

    from nebu.cli.main import cli
    # Use Current Working Directory (CWD)
    args = ['publish', '.', message]
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
    form = parse_multipart(io.BytesIO(request_data), {'boundary': boundary})
    assert form['publisher'][0] == publisher.encode('utf8')
    assert form['message'][0] == message.encode('utf8')
    # Check the zipfile for contents
    with zipfile.ZipFile(io.BytesIO(form['file'][0])) as zb:
        included_files = zb.namelist()
    expected_files = [
        'col11405/collection.xml',
        'col11405/m37154/index.cnxml',
        'col11405/m37217/index.cnxml',
        'col11405/m37386/index.cnxml',
        'col11405/m40645/index.cnxml',
        'col11405/m40646/index.cnxml',
        'col11405/m42303/index.cnxml',
        'col11405/m42304/index.cnxml',
    ]
    assert included_files == expected_files


def test_publish_cmd_outside_cwd(datadir, monkeypatch,
                                 requests_mocker, invoker):
    id = 'collection'
    publisher = 'CollegeStax'
    message = 'mEssAgE'
    monkeypatch.setenv('XXX_PUBLISHER', publisher)

    # Mock the publishing request
    url = 'https://cnx.org/api/v3/publish'
    resp_callback = ResponseCallback(COLLECTION_PUBLISH_PRESS_RESP_DATA)
    requests_mocker.register_uri('POST', url, status_code=200,
                                 text=resp_callback)

    from nebu.cli.main import cli
    # Use Current Working Directory (CWD)
    args = ['publish', str(datadir / id), message]
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
    form = parse_multipart(io.BytesIO(request_data), {'boundary': boundary})
    assert form['publisher'][0] == publisher.encode('utf8')
    assert form['message'][0] == message.encode('utf8')
    # Check the zipfile for contents
    with zipfile.ZipFile(io.BytesIO(form['file'][0])) as zb:
        included_files = zb.namelist()
    expected_files = [
        'col11405/collection.xml',
        'col11405/m37154/index.cnxml',
        'col11405/m37217/index.cnxml',
        'col11405/m37386/index.cnxml',
        'col11405/m40645/index.cnxml',
        'col11405/m40646/index.cnxml',
        'col11405/m42303/index.cnxml',
        'col11405/m42304/index.cnxml',
    ]
    assert included_files == expected_files


def test_publish_cmd_with_invalid_content(datadir, monkeypatch,
                                          requests_mocker, invoker):
    id = 'invalid_collection'
    publisher = 'CollegeStax'
    message = 'mEssAgE'
    monkeypatch.setenv('XXX_PUBLISHER', publisher)

    from nebu.cli.main import cli
    # Use Current Working Directory (CWD)
    args = ['publish', str(datadir / id), message]
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


def test_publish_cmd_with_errors(datadir, monkeypatch,
                                 requests_mocker, invoker):
    id = 'collection'
    publisher = 'CollegeStax'
    message = 'mEssAgE'
    monkeypatch.setenv('XXX_PUBLISHER', publisher)

    # Mock the publishing request
    url = 'https://cnx.org/api/v3/publish'
    requests_mocker.register_uri('POST', url, status_code=400,
                                 text='400')

    from nebu.cli.main import cli
    # Use Current Working Directory (CWD)
    args = ['publish', str(datadir / id), message]
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
