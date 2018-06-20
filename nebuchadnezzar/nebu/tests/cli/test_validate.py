class TestValidateCmd:

    def test_in_cwd(self, datadir, monkeypatch, invoker):
        id = 'collection'
        monkeypatch.chdir(str(datadir / id))

        from nebu.cli.main import cli
        args = ['validate']  # using Current Working Directory (CWD)
        result = invoker(cli, args)

        assert result.exit_code == 0
        assert result.output == 'All good! :)\n'

    def test_outside_cwd(self, datadir, invoker):
        path = datadir / 'collection'

        from nebu.cli.main import cli
        args = ['validate', str(path)]
        result = invoker(cli, args)

        assert result.exit_code == 0
        assert result.output == 'All good! :)\n'

    def test_with_invalid_content(self, datadir, monkeypatch, invoker):
        id = 'invalid_collection'
        monkeypatch.chdir(str(datadir / id))

        from nebu.cli.main import cli
        args = ['validate']  # using Current Working Directory (CWD)
        result = invoker(cli, args)

        assert result.exit_code == 0

        expected_output = (
            ('collection.xml:114:13 -- error: element "para" from '
             'namespace "http://cnx.rice.edu/cnxml" not allowed in '
             'this context'),
            'mux:mux is not a valid identifier',
            ('mux/index.cnxml:61:10 -- error: unknown element "foo" from '
             'namespace "http://cnx.rice.edu/cnxml"'),
        )
        for line in expected_output:
            assert line in result.output

        assert "We've got problems... :(" in result.output
