def test_for_list(monkeypatch, invoker):

    from nebu.cli.main import cli
    args = ['list']
    result = invoker(cli, args)
    assert result.exit_code == 0

    expected_output = 'test-env\t https://cnx.org\n'
    assert result.output == expected_output
