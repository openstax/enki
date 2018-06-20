from functools import partial
from os import scandir
from pathlib import Path


def pathlib_walk(dir):
    for e in scandir(str(dir)):
        yield Path(e.path)
        if e.is_dir():
            for ee in pathlib_walk(e.path):
                yield Path(ee)


def register_data_file(requests_mock, datadir, filename, url):
        datafile = datadir / filename
        content_size = datafile.stat().st_size
        with datafile.open('rb') as fb:
            headers = {'Content-Length': str(content_size)}
            requests_mock.get(
                url,
                content=fb.read(),
                headers=headers,
            )


class TestGetCmd:

    def test(self, datadir, tmpcwd, requests_mock, invoker):
        col_id = 'col11405'
        col_version = '1.2'
        col_uuid = 'b699648f-405b-429f-bf11-37bad4246e7c'
        col_hash = '{}@{}'.format(col_uuid, '2.1')
        base_url = 'https://archive.cnx.org'
        metadata_url = '{}/content/{}/{}'.format(base_url, col_id, col_version)
        extras_url = '{}/extras/{}'.format(base_url, col_hash)
        completezip_url = ('{}/exports'
                           '/b699648f-405b-429f-bf11-37bad4246e7c@2.1.zip'
                           '/intro-to-computational-engineering'
                           '-elec-220-labs-2.1.zip'.format(base_url)
                           )

        # Register the data urls
        for fname, url in (('contents.json', metadata_url),
                           ('extras.json', extras_url),
                           ('complete.zip', completezip_url)):
            register_data_file(requests_mock, datadir, fname, url)

        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id, col_version]
        result = invoker(cli, args)

        assert result.exit_code == 0

        dir = tmpcwd / col_id
        expected = datadir / 'collection'

        def _rel(p, b):
            return p.relative_to(b)

        relative_dir = map(partial(_rel, b=dir), pathlib_walk(dir))
        relative_expected = map(partial(_rel, b=expected),
                                pathlib_walk(expected))
        assert sorted(relative_dir) == sorted(relative_expected)

    def test_not_latest(self, datadir, tmpcwd, requests_mock,
                        monkeypatch, invoker):
        col_id = 'col11405'
        col_version = '1.1'
        col_latest = '2.1'
        col_uuid = 'b699648f-405b-429f-bf11-37bad4246e7c'
        col_hash = '{}@{}'.format(col_uuid, '1.1')
        base_url = 'https://archive.cnx.org'
        metadata_url = '{}/content/{}/{}'.format(base_url, col_id, col_version)
        extras_url = '{}/extras/{}'.format(base_url, col_hash)
        latest_url = '{}/extras/{}@{}'.format(base_url, col_uuid, col_latest)
        completezip_url = ('{}/exports'
                           '/b699648f-405b-429f-bf11-37bad4246e7c@1.1.zip'
                           '/intro-to-computational-engineering'
                           '-elec-220-labs-1.1.zip'.format(base_url)
                           )

        # Register the data urls
        for fname, url in (('contents_old.json', metadata_url),
                           ('extras_old.json', extras_url),
                           ('extras.json', latest_url),
                           ('complete.zip', completezip_url)):
            register_data_file(requests_mock, datadir, fname, url)

        # patch input to return 'y'
        monkeypatch.setattr('builtins.input', lambda x: "y")
        from nebu.cli.main import cli
        args = ['get', 'test-env', '-d', 'mydir', col_id, col_version]
        result = invoker(cli, args)

        assert result.exit_code == 0

        dir = tmpcwd / 'mydir'
        expected = datadir / 'collection'

        def _rel(p, b):
            return p.relative_to(b)

        relative_dir = map(partial(_rel, b=dir), pathlib_walk(dir))
        relative_expected = map(partial(_rel, b=expected),
                                pathlib_walk(expected))
        assert sorted(relative_dir) == sorted(relative_expected)

    def test_not_latest_abort(self, datadir, tmpcwd, requests_mock,
                              monkeypatch, invoker):
        col_id = 'col11405'
        col_version = '1.1'
        col_latest = '2.1'
        col_uuid = 'b699648f-405b-429f-bf11-37bad4246e7c'
        col_hash = '{}@{}'.format(col_uuid, '1.1')
        base_url = 'https://archive.cnx.org'
        metadata_url = '{}/content/{}/{}'.format(base_url, col_id, col_version)
        extras_url = '{}/extras/{}'.format(base_url, col_hash)
        latest_url = '{}/extras/{}@{}'.format(base_url, col_uuid, col_latest)

        # Register the data urls
        for fname, url in (('contents_old.json', metadata_url),
                           ('extras_old.json', extras_url),
                           ('extras.json', latest_url)):
            register_data_file(requests_mock, datadir, fname, url)

        # patch input to return 'y'
        monkeypatch.setattr('builtins.input', lambda x: "n")
        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id, col_version]
        result = invoker(cli, args)

        assert result.exit_code == 6

        msg = "Non-latest version requested"
        assert msg in result.output

    def test_latest(self, datadir, tmpcwd, requests_mock, invoker):
        col_id = 'col11405'
        col_version = 'latest'
        col_uuid = 'b699648f-405b-429f-bf11-37bad4246e7c'
        col_hash = '{}@{}'.format(col_uuid, '2.1')
        base_url = 'https://archive.cnx.org'
        metadata_url = '{}/content/{}/{}'.format(base_url, col_id, col_version)
        extras_url = '{}/extras/{}'.format(base_url, col_hash)
        completezip_url = ('{}/exports'
                           '/b699648f-405b-429f-bf11-37bad4246e7c@2.1.zip'
                           '/intro-to-computational-engineering'
                           '-elec-220-labs-2.1.zip'.format(base_url)
                           )

        # Register the data urls
        for fname, url in (('contents.json', metadata_url),
                           ('extras.json', extras_url),
                           ('complete.zip', completezip_url)):
            register_data_file(requests_mock, datadir, fname, url)

        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id, col_version]
        result = invoker(cli, args)

        assert result.exit_code == 0

        dir = tmpcwd / col_id
        expected = datadir / 'collection'

        def _rel(p, b):
            return p.relative_to(b)

        relative_dir = map(partial(_rel, b=dir), pathlib_walk(dir))
        relative_expected = map(partial(_rel, b=expected),
                                pathlib_walk(expected))
        assert sorted(relative_dir) == sorted(relative_expected)

    def test_with_existing_output_dir(self, tmpcwd, capsys, invoker):
        col_id = 'col00000'

        (tmpcwd / col_id).mkdir()

        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id, '1.1']
        result = invoker(cli, args)

        assert result.exit_code == 3

        assert 'directory already exists:' in result.output

    def test_failed_request_omitting_version(self, invoker):
        col_id = 'col00000'

        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id]
        result = invoker(cli, args)

        assert result.exit_code == 2

        assert 'Missing argument "col_version"' in result.output

    def test_failed_request_using_version(self, requests_mock, invoker):
        col_id = 'col00000'
        col_ver = '1.19'
        content_url = 'https://archive.cnx.org/content/{}/{}'.format(col_id,
                                                                     col_ver)

        requests_mock.get(content_url, status_code=404)

        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id, col_ver]
        result = invoker(cli, args)

        assert result.exit_code == 4

        msg = "content unavailable for '{}/{}'".format(col_id, col_ver)
        assert msg in result.output

    def test_unavailable_completezip(self, datadir, requests_mock, invoker):
        # This case is possible when the content exists, but the completezip
        # has not been produced.
        col_id = 'col11405'
        col_version = '1.2'
        col_uuid = 'b699648f-405b-429f-bf11-37bad4246e7c'
        col_hash = '{}@{}'.format(col_uuid, '2.1')
        base_url = 'https://archive.cnx.org'
        metadata_url = '{}/content/{}/{}'.format(base_url, col_id, col_version)
        extras_url = '{}/extras/{}'.format(base_url, col_hash)

        # Register the data urls
        for fname, url in (('contents.json', metadata_url),
                           ('missing_zip.json', extras_url)):
            register_data_file(requests_mock, datadir, fname, url)

        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id, col_version]
        result = invoker(cli, args)

        assert result.exit_code == 4

        msg = "The content exists, but the completezip is missing"
        assert msg in result.output

        msg = "content unavailable for '{}/{}'".format(col_id, col_version)
        assert msg in result.output

    def test_empty_zip(self, datadir, tmpcwd, requests_mock, invoker):
        col_id = 'col11405'
        col_version = '1.2'
        col_uuid = 'b699648f-405b-429f-bf11-37bad4246e7c'
        col_hash = '{}@{}'.format(col_uuid, '2.1')
        base_url = 'https://archive.cnx.org'
        metadata_url = '{}/content/{}/{}'.format(base_url, col_id, col_version)
        extras_url = '{}/extras/{}'.format(base_url, col_hash)
        completezip_url = ('{}/exports'
                           '/b699648f-405b-429f-bf11-37bad4246e7c@2.1.zip'
                           '/intro-to-computational-engineering'
                           '-elec-220-labs-2.1.zip'.format(base_url)
                           )

        # Register the data urls
        for fname, url in (('contents.json', metadata_url),
                           ('extras.json', extras_url)):
            register_data_file(requests_mock, datadir, fname, url)

        requests_mock.get(completezip_url, status_code=204)

        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id, col_version]
        result = invoker(cli, args)

        assert result.exit_code == 4

        msg = "The content exists, but the completezip is missing"
        assert msg in result.output

    def test_404_completezip(self, datadir, tmpcwd, requests_mock, invoker):
        col_id = 'col11405'
        col_version = '1.2'
        col_uuid = 'b699648f-405b-429f-bf11-37bad4246e7c'
        col_hash = '{}@{}'.format(col_uuid, '2.1')
        base_url = 'https://archive.cnx.org'
        metadata_url = '{}/content/{}/{}'.format(base_url, col_id, col_version)
        extras_url = '{}/extras/{}'.format(base_url, col_hash)
        completezip_url = ('{}/exports'
                           '/b699648f-405b-429f-bf11-37bad4246e7c@2.1.zip'
                           '/intro-to-computational-engineering'
                           '-elec-220-labs-2.1.zip'.format(base_url)
                           )

        # Register the data urls
        for fname, url in (('contents.json', metadata_url),
                           ('extras.json', extras_url)):
            register_data_file(requests_mock, datadir, fname, url)

        requests_mock.get(completezip_url, status_code=404)

        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id, col_version]
        result = invoker(cli, args)

        assert result.exit_code == 4

        msg = "content unavailable for '{}/{}'".format(col_id, col_version)
        assert msg in result.output
