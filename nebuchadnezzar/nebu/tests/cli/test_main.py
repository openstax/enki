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


def test_old_version(monkeypatch, invoker):
    version = '0.0.0'

    monkeypatch.setattr(nebu.cli.main, '__version__', version)

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


def test_bad_remote_url():
    from nebu.cli.main import get_remote_releases
    bad_url = "bad_url.!@#$%^&*()_+"
    path = []
    assert get_remote_releases(bad_url, path) == []


def test_bad_remote_path():
    from nebu.cli.main import get_remote_releases
    url = "https://pypi.org/pypi/nebuchadnezzar/json"
    bad_path = ["bad_path.!@#$%^&*()_+"]
    assert get_remote_releases(url, bad_path) == []


def test_no_versions_found():
    from nebu.cli.main import get_latest_released_version

    def empty_version_list():
        return []
    assert get_latest_released_version(empty_version_list) == ""
