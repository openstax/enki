class TestPingCmd:
    def test_auth_ping_internal_server_error(self, requests_mock, invoker):
        # Mock the auth ping request
        url = 'https://cnx.org/api/auth-ping'
        requests_mock.register_uri('GET', url, status_code=500,
                                   text='Internal server error')

        from nebu.cli.main import cli
        args = ['ping', 'test-env', '-u', 'someusername', '-p', 'somepassword']
        result = invoker(cli, args)

        assert result.exit_code == 1
        assert 'Internal server error' in result.output

        if result.exception and not isinstance(result.exception, SystemExit):
            raise result.exception

    def test_publish_ping_internal_server_error(self, requests_mock, invoker):
        # Mock the ping requests
        url = 'https://cnx.org/api/auth-ping'
        requests_mock.register_uri('GET', url, status_code=200,
                                   text='OK')
        url = 'https://cnx.org/api/publish-ping'
        requests_mock.register_uri('GET', url, status_code=500,
                                   text='Internal server error')

        from nebu.cli.main import cli
        args = ['ping', 'test-env', '-u', 'someusername', '-p', 'somepassword']
        result = invoker(cli, args)

        assert result.exit_code == 1
        assert 'Internal server error' in result.output

        if result.exception and not isinstance(result.exception, SystemExit):
            raise result.exception

    def test_bad_credentials(self, requests_mock, invoker):
        # Mock the auth ping request
        url = 'https://cnx.org/api/auth-ping'
        requests_mock.register_uri('GET', url, status_code=401,
                                   text='Nothing to see')

        from nebu.cli.main import cli
        args = ['ping', 'test-env', '-u', 'someusername', '-p', '!']
        result = invoker(cli, args)

        assert result.exit_code == 1
        assert 'Bad credentials' in result.output

        if result.exception and not isinstance(result.exception, SystemExit):
            raise result.exception

    def test_no_permission_to_publish(self, requests_mock, invoker):
        # Mock the ping requests
        url = 'https://cnx.org/api/auth-ping'
        requests_mock.register_uri('GET', url, status_code=200,
                                   text='OK')
        url = 'https://cnx.org/api/publish-ping'
        requests_mock.register_uri('GET', url, status_code=401,
                                   text='Nothing to see')

        from nebu.cli.main import cli
        args = ['ping', 'test-env', '-u', 'someusername', '-p', '!']
        result = invoker(cli, args)

        assert result.exit_code == 1
        assert 'Publishing not allowed' in result.output

        if result.exception and not isinstance(result.exception, SystemExit):
            raise result.exception

    def test_ok(self, requests_mock, invoker):
        # Mock the ping requests
        url = 'https://cnx.org/api/auth-ping'
        requests_mock.register_uri('GET', url, status_code=200,
                                   text='OK')
        url = 'https://cnx.org/api/publish-ping'
        requests_mock.register_uri('GET', url, status_code=200,
                                   text='OK')

        from nebu.cli.main import cli
        args = ['ping', 'test-env', '-u', 'someusername', '-p', '!']
        result = invoker(cli, args)

        assert result.exit_code == 0
        assert 'The user has permission to publish' in result.output

        if result.exception and not isinstance(result.exception, SystemExit):
            raise result.exception
