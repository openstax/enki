class TestValidateCmd:

    def test_in_cwd(self, datadir, monkeypatch, invoker):
        id = 'collection'
        monkeypatch.chdir(str(datadir / id))

        from nebu.cli.main import cli
        args = ['validate']  # using Current Working Directory (CWD)
        result = invoker(cli, args)

        assert result.exit_code == 0
        assert result.output == 'All good! :)\n'

    def test_outside_cwd(self, datadir, monkeypatch, invoker):
        path = datadir / 'collection'
        monkeypatch.chdir('/tmp')

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
            'mux:mux is not a valid identifier',
            ('collection.xml:114:13 -- error: element "cnx:para" not'
             ' allowed here; expected element "content", "declarations", '
             '"extensions", "featured-links" or "parameters"'
             ),
            ('mux/index.cnxml:61:10 -- error: element "foo" not allowed'
             ' anywhere; expected element "code", "definition", "div", '
             '"equation", "example", "exercise", "figure", "list", "media",'
             ' "note", "para", "preformat", "q:problemset", '
             '"quote", "rule", "section" or "table"'
             ),
        )

        for line in expected_output:
            assert line in result.output

        assert "We've got problems... :(" in result.output

    def test_outside_cwd_invalid_content(self, datadir, monkeypatch, invoker):
        path = datadir / 'invalid_collection'
        monkeypatch.chdir('/tmp')

        from nebu.cli.main import cli
        args = ['validate', str(path)]
        result = invoker(cli, args)

        assert result.exit_code == 0

        expected_output = (
            'mux:mux is not a valid identifier',
            ('collection.xml:114:13 -- error: element "cnx:para" not'
             ' allowed here; expected element "content", "declarations", '
             '"extensions", "featured-links" or "parameters"'
             ),
            ('mux/index.cnxml:61:10 -- error: element "foo" not allowed'
             ' anywhere; expected element "code", "definition", "div", '
             '"equation", "example", "exercise", "figure", "list", "media",'
             ' "note", "para", "preformat", "q:problemset", '
             '"quote", "rule", "section" or "table"'
             ),
        )

        for line in expected_output:
            assert line in result.output

        assert "We've got problems... :(" in result.output
