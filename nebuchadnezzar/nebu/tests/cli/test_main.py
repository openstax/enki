import nebu.cli.main


def test_for_version(monkeypatch, invoker):
    version = 'X.Y.Z'

    monkeypatch.setattr(nebu.cli.main, '__version__', version)

    from nebu.cli.main import cli
    args = ['--version']
    result = invoker(cli, args)
    assert result.exit_code == 0

    expected_output = 'Nebuchadnezzar {}\n'.format(version)
    assert result.output == expected_output
