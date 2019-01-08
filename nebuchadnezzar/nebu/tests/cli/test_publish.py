import io
import zipfile
from cgi import parse_multipart
from requests.auth import HTTPBasicAuth

import pretend


class MockRequest:
    def __init__(self):
        self.headers = {}


class ResponseCallback:
    """A response callback to be used with requests_mock"""

    def __init__(self, json_data):
        self.captured_request = None
        self.data = json_data

    def __call__(self, request, context):
        self.captured_request = request
        context.headers['content-type'] = 'text/json'
        import json
        return json.dumps(self.data)


def mock_successful_ping(ping_route, requests_mock):
    url = 'https://cnx.org/api{}'.format(ping_route)

    requests_mock.register_uri(
        'GET',
        url,
        status_code=200,
        text='200',
    )


# This is the response that would come out of Press given
# the data in data/collection.
COLLECTION_PUBLISH_PRESS_RESP_DATA = [
    {'id': 'col11405',
     'version': '1.3',
     'source_id': 'col11405',
     'url': 'https://cnx.org/content/col11405/1.3',
     },
    {'id': 'm37154',
     'version': '1.3',
     'source_id': 'm37154',
     'url': 'https://cnx.org/content/m37154/1.3',
     },
    {'id': 'm37217',
     'version': '1.3',
     'source_id': 'm37217',
     'url': 'https://cnx.org/content/m37217/1.3',
     },
    {'id': 'm37386',
     'version': '1.3',
     'source_id': 'm37386',
     'url': 'https://cnx.org/content/m37386/1.3',
     },
    {'id': 'm40645',
     'version': '1.3',
     'source_id': 'm40645',
     'url': 'https://cnx.org/content/m40645/1.3',
     },
    {'id': 'm40646',
     'version': '1.3',
     'source_id': 'm40646',
     'url': 'https://cnx.org/content/m40646/1.3',
     },
    {'id': 'm42303',
     'version': '1.3',
     'source_id': 'm42303',
     'url': 'https://cnx.org/content/m42303/1.3',
     },
    {'id': 'm42304',
     'version': '1.3',
     'source_id': 'm42304',
     'url': 'https://cnx.org/content/m42304/1.3',
     },
]


class TestPublishCmd:

    def test_in_cwd(self, datadir, monkeypatch, requests_mock, invoker):
        mock_successful_ping('/auth-ping', requests_mock)
        mock_successful_ping('/publish-ping', requests_mock)

        id = 'collection'
        publisher = 'CollegeStax'
        message = 'mEssAgE'
        monkeypatch.chdir(str(datadir / id))
        monkeypatch.setenv('XXX_PUBLISHER', publisher)

        # Mock the publishing request
        url = 'https://cnx.org/api/publish-litezip'
        resp_callback = ResponseCallback(COLLECTION_PUBLISH_PRESS_RESP_DATA)
        requests_mock.register_uri(
            'POST',
            url,
            status_code=200,
            text=resp_callback,
        )

        from nebu.cli.main import cli
        # Use Current Working Directory (CWD)
        args = ['publish', 'test-env', '.', '-m', message,
                '--username', 'someusername', '--password', 'somepassword']
        result = invoker(cli, args)

        # Check the results
        if result.exception:
            raise result.exception
        assert result.exit_code == 0
        expected_output = (
            'Great work!!! =D\n'
        )
        # FIXME Ignoring temporary formatting of output, just check for
        #       the last line so we know we got to the correct place.
        # assert result.output == expected_output
        assert expected_output in result.output

        # Check the sent contents
        request_data = resp_callback.captured_request._request.body
        # Discover the multipart/form-data boundry
        boundary = request_data.split(b'\r\n')[0][2:]
        form = parse_multipart(io.BytesIO(request_data),
                               {'boundary': boundary})
        assert form['publisher'][0] == publisher.encode('utf8')
        assert form['message'][0] == message.encode('utf8')
        # Check the zipfile for contents
        with zipfile.ZipFile(io.BytesIO(form['file'][0])) as zb:
            included_files = set(zb.namelist())
        expected_files = set((
            'col11405/collection.xml',
            'col11405/m37151/index.cnxml',
            'col11405/m37152/index.cnxml',
            'col11405/m37154/index.cnxml',
            'col11405/m37217/index.cnxml',
            'col11405/m37386/index.cnxml',
            'col11405/m40643/index.cnxml',
            'col11405/m40645/index.cnxml',
            'col11405/m40646/index.cnxml',
            'col11405/m42302/index.cnxml',
            'col11405/m42303/index.cnxml',
            'col11405/m42304/index.cnxml'
        ))
        assert included_files == expected_files

    def test_with_resource(self, datadir, monkeypatch, requests_mock, invoker):
        mock_successful_ping('/auth-ping', requests_mock)
        mock_successful_ping('/publish-ping', requests_mock)

        dir_name = 'collection_resources'
        publisher = 'CollegeStax'
        message = 'mEssAgE'
        monkeypatch.chdir(str(datadir / dir_name))
        monkeypatch.setenv('XXX_PUBLISHER', publisher)

        # Mock the publishing request
        url = 'https://cnx.org/api/publish-litezip'
        resp_callback = ResponseCallback(COLLECTION_PUBLISH_PRESS_RESP_DATA)
        requests_mock.register_uri(
            'POST',
            url,
            status_code=200,
            text=resp_callback,
        )

        from nebu.cli.main import cli
        # Use Current Working Directory (CWD)
        args = ['publish', 'test-env', '.', '-m', message,
                '--username', 'someusername', '--password', 'somepassword']
        result = invoker(cli, args)

        # Check the results
        if result.exception:
            raise result.exception
        assert result.exit_code == 0
        expected_output = (
            'Great work!!! =D\n'
        )
        # FIXME Ignoring temporary formatting of output, just check for
        #       the last line so we know we got to the correct place.
        # assert result.output == expected_output
        assert expected_output in result.output

        # Check the sent contents
        request_data = resp_callback.captured_request._request.body
        # Discover the multipart/form-data boundry
        boundary = request_data.split(b'\r\n')[0][2:]
        form = parse_multipart(io.BytesIO(request_data),
                               {'boundary': boundary})
        assert form['publisher'][0] == publisher.encode('utf8')
        assert form['message'][0] == message.encode('utf8')
        # Check the zipfile for contents
        with zipfile.ZipFile(io.BytesIO(form['file'][0])) as zb:
            included_files = set(zb.namelist())
        expected_files = set((
            'col11405/collection.xml',
            'col11405/LEaRN.png',
            'col11405/m37154/LEaRN.png',
            'col11405/m37154/index.cnxml',
            # NOTE: The following files are commented out to create the
            # expectation that we only publish content that has changed.
            # See test_publish_only_what_changed for more info.
            # 'col11405/m37217/index.cnxml',
            # 'col11405/m37386/index.cnxml',
            # 'col11405/m40645/index.cnxml',
            # 'col11405/m40646/index.cnxml',
            # 'col11405/m42303/index.cnxml',
            # 'col11405/m42304/index.cnxml',
        ))
        assert included_files == expected_files

    def test_outside_cwd(self, datadir, monkeypatch,
                         requests_mock, invoker):
        mock_successful_ping('/auth-ping', requests_mock)
        mock_successful_ping('/publish-ping', requests_mock)

        id = 'collection'
        publisher = 'CollegeStax'
        message = 'mEssAgE'
        monkeypatch.setenv('XXX_PUBLISHER', publisher)

        # Mock the publishing request
        url = 'https://cnx.org/api/publish-litezip'
        resp_callback = ResponseCallback(COLLECTION_PUBLISH_PRESS_RESP_DATA)
        requests_mock.register_uri(
            'POST',
            url,
            status_code=200,
            text=resp_callback,
        )

        from nebu.cli.main import cli
        # Use Current Working Directory (CWD)
        args = ['publish', 'test-env', str(datadir / id), '-m', message,
                '--username', 'someusername', '--password', 'somepassword']
        result = invoker(cli, args)

        # Check the results
        if result.exception:
            raise result.exception
        assert result.exit_code == 0
        expected_output = (
            'Great work!!! =D\n'
        )
        # FIXME Ignoring temporary formatting of output, just check for
        #       the last line so we know we got to the correct place.
        # assert result.output == expected_output
        assert expected_output in result.output

        # Check the sent contents
        request_data = resp_callback.captured_request._request.body
        # Discover the multipart/form-data boundry
        boundary = request_data.split(b'\r\n')[0][2:]
        form = parse_multipart(io.BytesIO(request_data),
                               {'boundary': boundary})
        assert form['publisher'][0] == publisher.encode('utf8')
        assert form['message'][0] == message.encode('utf8')
        # Check the zipfile for contents
        with zipfile.ZipFile(io.BytesIO(form['file'][0])) as zb:
            included_files = set(zb.namelist())
        expected_files = set((
            'col11405/collection.xml',
            'col11405/m37151/index.cnxml',
            'col11405/m37152/index.cnxml',
            'col11405/m37154/index.cnxml',
            'col11405/m37217/index.cnxml',
            'col11405/m37386/index.cnxml',
            'col11405/m40643/index.cnxml',
            'col11405/m40645/index.cnxml',
            'col11405/m40646/index.cnxml',
            'col11405/m42302/index.cnxml',
            'col11405/m42303/index.cnxml',
            'col11405/m42304/index.cnxml'
        ))
        assert included_files == expected_files

    def test_with_invalid_content(self, datadir, monkeypatch,
                                  requests_mock, invoker):
        mock_successful_ping('/auth-ping', requests_mock)
        mock_successful_ping('/publish-ping', requests_mock)

        id = 'invalid_collection'
        publisher = 'CollegeStax'
        message = 'mEssAgE'
        monkeypatch.setenv('XXX_PUBLISHER', publisher)

        from nebu.cli.main import cli
        # Use Current Working Directory (CWD)
        args = ['publish', 'test-env', str(datadir / id), '-m', message,
                '--username', 'someusername', '--password', 'somepassword']
        result = invoker(cli, args)

        # Check the results
        if result.exception and not isinstance(result.exception, SystemExit):
            raise result.exception
        assert result.exit_code == 1
        # Check for the expected failure marker message.
        expected_output = (
            "We've got problems... :(\n"
        )
        assert expected_output in result.output

    def test_with_publish_auth_error(self, datadir, monkeypatch,
                                     requests_mock, invoker):
        mock_successful_ping('/auth-ping', requests_mock)

        # Mock unsuccessful publish ping
        publish_ping_url = 'https://cnx.org/api/publish-ping'
        requests_mock.register_uri(
            'GET',
            publish_ping_url,
            status_code=401,
            text='401',
        )

        id = 'collection'
        publisher = 'CollegeStax'
        message = 'mEssAgE'
        monkeypatch.setenv('XXX_PUBLISHER', publisher)

        from nebu.cli.main import cli
        # Use Current Working Directory (CWD)
        args = ['publish', 'test-env', str(datadir / id), '-m', message,
                '--username', 'username', '--password', 'password']
        result = invoker(cli, args)

        # Check the results
        if result.exception and not isinstance(result.exception, SystemExit):
            raise result.exception
        assert result.exit_code == 1
        # Check for the expected failure output.
        assert 'Publishing not allowed: ' in result.output
        expected_output = (
            'Stop the Press!!! =()\n'
        )
        # FIXME Ignoring temporary formatting of output, just check for
        #       the last line so we know we got to the correct place.
        # assert result.output == expected_output
        assert expected_output in result.output

    def test_auth_good_credentials_and_can_publish(self, datadir, monkeypatch,
                                                   requests_mock, invoker):
        """Test that the options are accepted when publishing.
        """
        mock_successful_ping('/auth-ping', requests_mock)
        mock_successful_ping('/publish-ping', requests_mock)

        id = 'collection'
        publisher = 'CollegeStax'
        message = 'mEssAgE'
        monkeypatch.setenv('XXX_PUBLISHER', publisher)

        # Mock the publishing request
        url = 'https://cnx.org/api/publish-litezip'
        auth = HTTPBasicAuth('username', 'password')
        mock_request = MockRequest()
        auth(mock_request)

        requests_mock.register_uri(
            'POST',
            url,
            status_code=200,
            text='200',
            request_headers=mock_request.headers
        )

        from nebu.cli.main import cli
        # Use Current Working Directory (CWD)
        args = ['publish', 'test-env', str(datadir / id), '-m', message,
                '--username', 'username', '--password', 'password']
        result = invoker(cli, args)

        # Check the results
        if result.exception and not isinstance(result.exception, SystemExit):
            raise result.exception
        assert result.exit_code == 0
        expected_output = (
            'Great work!!! =D\n'
        )
        # FIXME Ignoring temporary formatting of output, just check for
        #       the last line so we know we got to the correct place.
        # assert result.output == expected_output
        assert expected_output in result.output

    def test_auth_no_permission_to_publish(self, datadir, monkeypatch,
                                           requests_mock, invoker):
        """
        Test what happens when user has good credentials but
        no permission to publish.
        """
        mock_successful_ping('/auth-ping', requests_mock)

        # Mock the unsuccessful publishing request
        publish_ping_url = 'https://cnx.org/api/publish-ping'
        requests_mock.register_uri(
            'GET',
            publish_ping_url,
            status_code=401,
            text='401'
        )

        id = 'collection'
        publisher = 'CollegeStax'
        message = 'mEssAgE'
        monkeypatch.setenv('XXX_PUBLISHER', publisher)

        from nebu.cli.main import cli
        # Use Current Working Directory (CWD)
        args = ['publish', 'test-env', str(datadir / id), '-m', message,
                '--username', 'username', '--password', 'password']
        result = invoker(cli, args)

        # Check the results
        if result.exception and not isinstance(result.exception, SystemExit):
            raise result.exception
        assert result.exit_code == 1
        # FIXME Ignoring temporary formatting of output, just check for
        #       the last line so we know we got to the correct place.
        # assert result.output == expected_output
        assert 'Publishing not allowed: ' in result.output
        assert 'Stop the Press!!! =()\n' in result.output

    def test_with_errors(self, datadir, monkeypatch,
                         requests_mock, invoker):
        mock_successful_ping('/auth-ping', requests_mock)
        mock_successful_ping('/publish-ping', requests_mock)

        id = 'collection'
        publisher = 'CollegeStax'
        message = 'mEssAgE'
        monkeypatch.setenv('XXX_PUBLISHER', publisher)

        # Mock the publishing request
        url = 'https://cnx.org/api/publish-litezip'
        requests_mock.register_uri(
            'POST',
            url,
            status_code=400,
            text='400',
        )

        from nebu.cli.main import cli
        # Use Current Working Directory (CWD)
        args = ['publish', 'test-env', str(datadir / id), '-m', message,
                '--username', 'username', '--password', 'password']
        result = invoker(cli, args)

        # Check the results
        if result.exception and not isinstance(result.exception, SystemExit):
            raise result.exception
        assert result.exit_code == 1
        # Check for the expected failure output.
        assert 'ERROR: ' in result.output
        expected_output = (
            'Stop the Press!!! =()\n'
        )
        # FIXME Ignoring temporary formatting of output, just check for
        #       the last line so we know we got to the correct place.
        # assert result.output == expected_output
        assert expected_output in result.output

    def test_skip_validation(self, datadir, monkeypatch, requests_mock,
                             invoker):
        mock_successful_ping('/auth-ping', requests_mock)
        mock_successful_ping('/publish-ping', requests_mock)

        id = 'collection'
        publisher = 'CollegeStax'
        message = 'mEssAgE'
        monkeypatch.chdir(str(datadir / id))
        monkeypatch.setenv('XXX_PUBLISHER', publisher)

        # Mock the publishing request
        url = 'https://cnx.org/api/publish-litezip'
        resp_callback = ResponseCallback(COLLECTION_PUBLISH_PRESS_RESP_DATA)
        requests_mock.register_uri(
            'POST',
            url,
            status_code=200,
            text=resp_callback,
        )

        # Stub the call for validation
        is_valid = pretend.call_recorder(lambda s: False)
        from nebu.cli import publish
        monkeypatch.setattr(publish, 'is_valid', is_valid)

        from nebu.cli.main import cli
        # Use Current Working Directory (CWD)
        args = ['publish', '--skip-validation', 'test-env', '.', '-m', message,
                '--username', 'someusername', '--password', 'somepassword']
        result = invoker(cli, args)

        # Check the results
        if result.exception:
            raise result.exception
        assert result.exit_code == 0
        expected_output = (
            'Great work!!! =D\n'
        )
        assert expected_output in result.output
        assert is_valid.calls == []

    def test_auth_bad_credentials(self, datadir, monkeypatch,
                                  requests_mock, invoker):
        # Mock unsuccessful auth ping
        auth_ping_url = 'https://cnx.org/api/auth-ping'
        requests_mock.register_uri(
            'GET',
            auth_ping_url,
            status_code=401,
            text='401',
        )

        id = 'collection'
        publisher = 'CollegeStax'
        message = 'mEssAgE'
        monkeypatch.setenv('XXX_PUBLISHER', publisher)

        from nebu.cli.main import cli
        # Use Current Working Directory (CWD)
        args = ['publish', 'test-env', str(datadir / id), '-m', message,
                '--username', 'username', '--password', 'password']
        result = invoker(cli, args)

        # Check the results
        if result.exception and not isinstance(result.exception, SystemExit):
            raise result.exception
        assert result.exit_code == 1
        # Check for the expected failure output.
        assert 'Bad credentials: ' in result.output
        expected_output = (
            'Stop the Press!!! =()\n'
        )
        # FIXME Ignoring temporary formatting of output, just check for
        #       the last line so we know we got to the correct place.
        # assert result.output == expected_output
        assert expected_output in result.output

    def test_publish_only_what_changed(self, datadir, monkeypatch,
                                       requests_mock, invoker):
        mock_successful_ping('/auth-ping', requests_mock)
        mock_successful_ping('/publish-ping', requests_mock)

        contents_folder = 'collection_resources'
        publisher = 'CollegeStax'
        message = 'mEssAgE'
        monkeypatch.chdir(str(datadir / contents_folder))
        monkeypatch.setenv('XXX_PUBLISHER', publisher)

        # Mock the publishing request
        url = 'https://cnx.org/api/publish-litezip'
        resp_callback = ResponseCallback(COLLECTION_PUBLISH_PRESS_RESP_DATA)
        requests_mock.register_uri(
            'POST',
            url,
            status_code=200,
            text=resp_callback,
        )

        from nebu.cli.main import cli
        # Use Current Working Directory (CWD)
        args = ['publish', 'test-env', '.', '-m', message,
                '--username', 'someusername', '--password', 'somepassword']
        result = invoker(cli, args)

        # Check the results
        if result.exception:
            raise result.exception
        assert result.exit_code == 0
        expected_output = (
            'Great work!!! =D\n'
        )
        # FIXME Ignoring temporary formatting of output, just check for
        #       the last line so we know we got to the correct place.
        # assert result.output == expected_output
        assert expected_output in result.output

        # Check the sent contents
        request_data = resp_callback.captured_request._request.body
        # Discover the multipart/form-data boundry
        boundary = request_data.split(b'\r\n')[0][2:]
        form = parse_multipart(io.BytesIO(request_data),
                               {'boundary': boundary})
        assert form['publisher'][0] == publisher.encode('utf8')
        assert form['message'][0] == message.encode('utf8')
        # Check the zipfile for contents
        with zipfile.ZipFile(io.BytesIO(form['file'][0])) as zb:
            actual_published = set(zb.namelist())
        expected_published = set((
            # Although these commented out files do exist in the directory,
            # they will not be published because their cached sha1 and
            # actual/calculated sha1 are equal, meaning there are no changes.
            # 'col11405/m37217/index.cnxml',
            # 'col11405/m37386/index.cnxml',
            # 'col11405/m40645/index.cnxml',
            # 'col11405/m40646/index.cnxml',
            # 'col11405/m42303/index.cnxml',
            # 'col11405/m42304/index.cnxml',

            # This one won't be in the cache (.sha1sum) file
            # to pretend that it's a new image:
            'col11405/m37154/LEaRN.png',
            # This one will have a different sha1 in the cache file
            # to pretend that it was modified:
            'col11405/m37154/index.cnxml',
            # Also this one will have a different sha1 in the cache file
            # to pretend that it was modified:
            'col11405/LEaRN.png',
            # Since modules were modified, also assume the collection
            # was modified:
            'col11405/collection.xml',
        ))

        assert actual_published == expected_published

    def test_publish_cmd_with_no_cache(self, datadir, monkeypatch,
                                       requests_mock, invoker):
        """Test what happens when there is no .sha1sum file in any dir.
        """
        mock_successful_ping('/auth-ping', requests_mock)
        mock_successful_ping('/publish-ping', requests_mock)

        contents_folder = 'collection'
        publisher = 'CollegeStax'
        message = 'mEssAgE'
        monkeypatch.chdir(str(datadir / contents_folder))
        monkeypatch.setenv('XXX_PUBLISHER', publisher)

        # Mock the publishing request
        url = 'https://cnx.org/api/publish-litezip'
        resp_callback = ResponseCallback(COLLECTION_PUBLISH_PRESS_RESP_DATA)
        requests_mock.register_uri(
            'POST',
            url,
            status_code=200,
            text=resp_callback,
        )

        from nebu.cli.main import cli
        # Use Current Working Directory (CWD)
        args = ['publish', 'test-env', '.', '-m', message,
                '--username', 'someusername', '--password', 'somepassword']
        result = invoker(cli, args)

        # Check the results
        if result.exception:
            raise result.exception
        assert result.exit_code == 0
        expected_output = (
            'Great work!!! =D\n'
        )
        # FIXME Ignoring temporary formatting of output, just check for
        #       the last line so we know we got to the correct place.
        # assert result.output == expected_output
        assert expected_output in result.output

        # Check the sent contents
        request_data = resp_callback.captured_request._request.body
        # Discover the multipart/form-data boundry
        boundary = request_data.split(b'\r\n')[0][2:]
        form = parse_multipart(io.BytesIO(request_data),
                               {'boundary': boundary})
        assert form['publisher'][0] == publisher.encode('utf8')
        assert form['message'][0] == message.encode('utf8')
        # Check the zipfile for contents
        with zipfile.ZipFile(io.BytesIO(form['file'][0])) as zb:
            actual_published = set(zb.namelist())

        # There is no .sha1sum file in any of the directories within
        # data/collection folder, so it should treat all files as new and
        # publish them all.
        expected_published = set((
            'col11405/collection.xml',
            'col11405/m37151/index.cnxml',
            'col11405/m37152/index.cnxml',
            'col11405/m37154/index.cnxml',
            'col11405/m37217/index.cnxml',
            'col11405/m37386/index.cnxml',
            'col11405/m40643/index.cnxml',
            'col11405/m40645/index.cnxml',
            'col11405/m40646/index.cnxml',
            'col11405/m42302/index.cnxml',
            'col11405/m42303/index.cnxml',
            'col11405/m42304/index.cnxml'
        ))
        assert actual_published == expected_published

    def test_publish_only_what_changed_with_tree(self, datadir, monkeypatch,
                                                 requests_mock, invoker):
        mock_successful_ping('/auth-ping', requests_mock)
        mock_successful_ping('/publish-ping', requests_mock)

        contents_folder = 'book_tree_cached'
        publisher = 'CollegeStax'
        message = 'mEssAgE'
        monkeypatch.chdir(str(datadir / contents_folder))
        monkeypatch.setenv('XXX_PUBLISHER', publisher)

        # Mock the publishing request
        url = 'https://cnx.org/api/publish-litezip'
        resp_callback = ResponseCallback(COLLECTION_PUBLISH_PRESS_RESP_DATA)
        requests_mock.register_uri(
            'POST',
            url,
            status_code=200,
            text=resp_callback,
        )

        from nebu.cli.main import cli
        # Use Current Working Directory (CWD)
        args = ['publish', 'test-env', '.', '-m', message,
                '--username', 'someusername', '--password', 'somepassword']
        result = invoker(cli, args)

        # Check the results
        if result.exception:
            raise result.exception
        assert result.exit_code == 0
        expected_output = (
            'Great work!!! =D\n'
        )
        # FIXME Ignoring temporary formatting of output, just check for
        #       the last line so we know we got to the correct place.
        # assert result.output == expected_output
        assert expected_output in result.output

        # Check the sent contents
        request_data = resp_callback.captured_request._request.body
        # Discover the multipart/form-data boundry
        boundary = request_data.split(b'\r\n')[0][2:]
        form = parse_multipart(io.BytesIO(request_data),
                               {'boundary': boundary})
        assert form['publisher'][0] == publisher.encode('utf8')
        assert form['message'][0] == message.encode('utf8')
        # Check the zipfile for contents
        with zipfile.ZipFile(io.BytesIO(form['file'][0])) as zb:
            actual_published = set(zb.namelist())
        expected_published = set((
            'col11405/collection.xml',
            'col11405/m42302/index.cnxml',
        ))

        assert actual_published == expected_published

    def test_nothing_changed(self, datadir, monkeypatch,
                             requests_mock, invoker):
        mock_successful_ping('/auth-ping', requests_mock)
        mock_successful_ping('/publish-ping', requests_mock)

        contents_folder = 'collection_no_changes'
        publisher = 'CollegeStax'
        message = 'mEssAgE'
        monkeypatch.chdir(str(datadir / contents_folder))
        monkeypatch.setenv('XXX_PUBLISHER', publisher)

        # Mock the publishing request
        url = 'https://cnx.org/api/publish-litezip'
        resp_callback = ResponseCallback(COLLECTION_PUBLISH_PRESS_RESP_DATA)
        requests_mock.register_uri(
            'POST',
            url,
            status_code=200,
            text=resp_callback,
        )

        from nebu.cli.main import cli
        # Use Current Working Directory (CWD)
        args = ['publish', 'test-env', '.', '-m', message,
                '--username', 'someusername', '--password', 'somepassword']
        result = invoker(cli, args)

        # Check the results
        if result.exception and not isinstance(result.exception, SystemExit):
            raise result.exception
        assert result.exit_code == 1
        expected_output = (
            'Nothing changed, nothing to publish.\n'
        )
        # FIXME Ignoring temporary formatting of output, just check for
        #       the last line so we know we got to the correct place.
        # assert result.output == expected_output
        assert expected_output in result.output
