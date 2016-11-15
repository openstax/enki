# -*- coding: utf-8 -*-
from functools import partial

import pytest


@pytest.fixture
def patched_discovery(monkeypatch):
    from nebu.cli import main as module

    def test_cmd(_):
        from nebu.logger import logger
        logger.info("InfO")
        logger.debug("dEbUg")
        logger.error("ErrOr")
        return 0

    def patched_func(parser):
        sub_parsers = parser.add_subparsers()
        test_parser = sub_parsers.add_parser('test')
        # Assign the command's execution function to the wrapped function.
        test_parser.set_defaults(cmd=test_cmd)

    monkeypatch.setattr(module, 'discover_subcommands',
                        patched_func)


@pytest.mark.usefixtures('patched_discovery')
def test_main(capsys):
    from nebu.cli.main import main
    args = ['test']
    return_code = main(args)
    assert return_code == 0

    out, err = capsys.readouterr()
    assert "InfO" not in out
    assert "dEbUg" not in out
    assert "ErrOr" in out


@pytest.mark.usefixtures('patched_discovery')
def test_main_with_verbosity(capsys):
    from nebu.cli.main import main
    args = ['-v', 'test']
    return_code = main(args)
    assert return_code == 0

    out, err = capsys.readouterr()
    assert "InfO" in out
    assert "dEbUg" in out
    assert "ErrOr" in out


@pytest.mark.usefixtures('patched_discovery')
def test_main_without_verbosity(capsys):
    from nebu.cli.main import main
    args = ['-q', 'test']
    return_code = main(args)
    assert return_code == 0

    out, err = capsys.readouterr()
    assert '' == out
