from copy import deepcopy

import pretend
import pytest


from nebu.cli._common import common_params, confirm, get_base_url, \
    build_archive_url


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

    def test_fallback_shortname(self):
        env_name = 'foo'
        url = 'https://foo.cnx.org'
        settings = {
            'settings': {'environs': {}},
        }
        ctx = pretend.stub(obj=settings)
        resulting_url = get_base_url(ctx, env_name)
        assert resulting_url == url

    def test_fallback_fqdn(self):
        env_name = 'foo.com'
        url = 'https://foo.com'
        settings = {
            'settings': {'environs': {}},
        }
        ctx = pretend.stub(obj=settings)
        resulting_url = get_base_url(ctx, env_name)
        assert resulting_url == url

    def test_fallback_fqdn_with_protocol(self):
        env_name = 'http://insecure.foo.com'
        url = 'http://insecure.foo.com'
        settings = {
            'settings': {'environs': {}},
        }
        ctx = pretend.stub(obj=settings)
        resulting_url = get_base_url(ctx, env_name)
        assert resulting_url == url


def test_build_archive_url():
    # Tuples of ("url", "expected_archive_url")
    test_urls = [
        ('https://dev.cnx.org', 'https://archive-dev.cnx.org'),
        ('https://qa.cnx.org', 'https://archive-qa.cnx.org'),
        ('https://staging.cnx.org', 'https://archive-staging.cnx.org'),
        ('https://content01.cnx.org', 'https://archive-content01.cnx.org'),
        ('https://cnx.org', 'https://archive.cnx.org'),
        ('https://local.cnx.org', 'https://archive-local.cnx.org')
    ]

    for url, expected in test_urls:
        env_name = 'test'
        settings = {
            'settings': {'environs': {env_name: {'url': url}}},
        }
        ctx = pretend.stub(obj=settings)
        resulting_url = build_archive_url(ctx, env_name)
        assert resulting_url == expected


def test_build_archive_url_with_config():
    env_name = 'test'
    url = 'https://archive.local.cnx.org'
    settings = {
        'settings': {
            'environs': {
                env_name: {
                    'url': 'https://local.cnx.org',
                    'archive_url': url
                }
            }
        },
    }
    ctx = pretend.stub(obj=settings)
    resulting_url = build_archive_url(ctx, env_name)
    assert resulting_url == url


def test_confirm(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda x: "y")
    result = confirm()

    assert result is True

    monkeypatch.setattr('builtins.input', lambda x: "n")
    result = confirm()

    assert result is False
