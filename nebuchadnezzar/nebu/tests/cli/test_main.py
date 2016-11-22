# -*- coding: utf-8 -*-
from copy import deepcopy
from functools import partial

import pytest


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
