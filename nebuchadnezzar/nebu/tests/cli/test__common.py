from copy import deepcopy

import pretend
import pytest


from nebu.cli._common import common_params, confirm, get_base_url
from nebu.cli.exceptions import UnknownEnvironment


@pytest.fixture
def faux_cmd(monkeypatch):
    from nebu.cli import main as module
    cmd_grp = deepcopy(module.cli)
    monkeypatch.setattr(module, 'cli', cmd_grp)

    @cmd_grp.command()
    @common_params
    def test():
        from nebu.logger import logger
        logger.info("InfO")
        logger.debug("dEbUg")
        logger.error("ErrOr")


@pytest.mark.usefixtures('faux_cmd')
def test_main(invoker):
    # FIXME should be a faux command group
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
    # FIXME should be a faux command group
    from nebu.cli.main import cli
    args = ['test', '-v']
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


def test_confirm(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda x: "y")
    result = confirm()

    assert result is True

    monkeypatch.setattr('builtins.input', lambda x: "n")
    result = confirm()

    assert result is False
