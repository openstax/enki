import nebu.cli.main


def test_for_version(monkeypatch, invoker):
    version = 'X.Y.Z'

    monkeypatch.setattr(nebu.cli.main, '__version__', version)

    from nebu.cli.main import cli
    args = ['--version']
    result = invoker(cli, args)
    assert result.exit_code == 0

    expected_output = 'Nebuchadnezzar {}\n'.format(version)
    expected_output += "The semantic version of Neb could not be read.\n"
    expected_output += "Please submit a bug report.\n"
    assert result.output == expected_output


def test_old_version(monkeypatch, invoker, requests_mock):
    version = '0.0.0'

    monkeypatch.setattr(nebu.cli.main, '__version__', version)

    content = b'{"releases": {"0.0.0": [], "1.0.0": []}}'
    content_size = len(content)
    headers = {'Content-Length': str(content_size)}
    requests_mock.get(
        "https://pypi.org/pypi/nebuchadnezzar/json",
        content=content,
        headers=headers,
    )

    from nebu.cli.main import cli
    args = ['--version']
    result = invoker(cli, args)
    assert result.exit_code == 0

    import re
    expected_output = 'Nebuchadnezzar {}\n'.format(version)
    expected_output += "Version available for install.\n"
    output_no_version = re.sub(r"Version \w+(\.\w+)* available",
                               "Version available",
                               result.output)
    assert output_no_version == expected_output


def test_bad_remote_url(requests_mock):
    from nebu.cli.main import get_remote_releases
    bad_url = "bad_url.!@#$%^&*()_+"

    requests_mock.get(
        bad_url,
        text='Not Found',
        status_code=404,
    )
    path = []
    assert get_remote_releases(bad_url, path) == []


def test_bad_remote_path(requests_mock):
    from nebu.cli.main import get_remote_releases
    url = "https://pypi.org/pypi/nebuchadnezzar/json"

    content = b'{"releases": {"0.0.0": [], "1.0.0": []}}'
    content_size = len(content)
    headers = {'Content-Length': str(content_size)}
    requests_mock.get(
        "https://pypi.org/pypi/nebuchadnezzar/json",
        content=content,
        headers=headers,
    )

    bad_path = ["bad_path.!@#$%^&*()_+"]
    assert get_remote_releases(url, bad_path) == []


def test_no_versions_found():
    from nebu.cli.main import get_latest_released_version

    def empty_version_list():
        return []
    assert get_latest_released_version(empty_version_list) == ""


def test_help_formatter(invoker):
    import textwrap
    import click
    from nebu.cli.main import HelpSectionsGroup

    @click.group(cls=HelpSectionsGroup)
    def cli(ctx):
        pass

    @cli.command(help_section='a')
    def a():
        pass

    @cli.command(help_section='b')
    def b():
        pass

    args = ['--help']
    result = invoker(cli, args)

    assert result.exit_code == 0

    expected_output = textwrap.dedent("""
    Usage: cli [OPTIONS] COMMAND [ARGS]...

    Options:
      --help  Show this message and exit.

    Commands:
      [a]
      a

      [b]
      b
    """)

    assert ('\n' + result.output) == expected_output


def test_help_formatter_no_cmd(invoker):
    import textwrap
    import click
    from nebu.cli.main import HelpSectionsGroup

    @click.group(cls=HelpSectionsGroup)
    def cli(ctx):
        pass

    args = ['--help']
    result = invoker(cli, args)

    assert result.exit_code == 0

    expected_output = textwrap.dedent("""
    Usage: cli [OPTIONS] COMMAND [ARGS]...

    Options:
      --help  Show this message and exit.
    """)

    assert ('\n' + result.output) == expected_output
