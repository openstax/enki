# -*- coding: utf-8 -*-
from copy import deepcopy
from functools import partial
from pathlib import Path
from os import scandir

import pytest
import requests_mock


###
# Helpers
###


def pathlib_walk(dir):
    for e in scandir(str(dir)):
        yield Path(e.path)
        if e.is_dir():
            for ee in pathlib_walk(e.path):
                yield Path(ee)


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
    url = 'http://legacy.cnx.org/content/{}/latest/complete'.format(col_id)

    with (datadir / 'complete.zip').open('rb') as fb:
        requests_mocker.get(url, content=fb.read())

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
    url = 'http://legacy.cnx.org/content/{}/latest/complete'.format(col_id)

    requests_mocker.register_uri('GET', url, status_code=404)

    from nebu.cli.main import cli
    args = ['get', col_id]
    result = invoker(cli, args)

    assert result.exit_code == 4

    msg = "content unavailable for '{}/latest'".format(col_id)
    assert msg in result.output
