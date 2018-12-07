from functools import partial
from os import scandir
from pathlib import Path


def pathlib_walk(dir):
    for e in scandir(str(dir)):
        if '.sha1sum' not in e.path:  # ignore .sha1sum files
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


def register_404(requests_mock, url):
            requests_mock.get(
                url,
                text='Not Found',
                status_code=404,
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

        # Register the data urls
        for fname, url in (('contents.json', metadata_url),
                           ('extras.json', extras_url),
                           ):
            register_data_file(requests_mock, datadir, fname, url)

        # Register the resources
        resdir = datadir / 'resources'
        for res in resdir.glob('*'):
            url = '{}/resources/{}'.format(base_url, res.relative_to(resdir))
            register_data_file(requests_mock, resdir, res, url)

        # Register contents
        condir = datadir / 'contents'
        for con in condir.glob('*'):
            url = '{}/contents/{}'.format(base_url, con.relative_to(condir))
            register_data_file(requests_mock, condir, con, url)

        # Register subcollection/chapter as 404
        register_404(requests_mock,
                     'https://archive.cnx.org/contents/'
                     '8ddfc8de-5164-5828-9fed-d0ed17edb489@2.1')

        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id, col_version]
        result = invoker(cli, args)

        assert result.exit_code == 0

        dir = tmpcwd / '{}_1.{}'.format(col_id, '2.1')
        expected = datadir / 'collection'

        def _rel(p, b):
            return p.relative_to(b)

        relative_dir = map(partial(_rel, b=dir), pathlib_walk(dir))
        relative_expected = map(partial(_rel, b=expected),
                                pathlib_walk(expected))
        assert sorted(relative_dir) == sorted(relative_expected)

    def test_outside_cwd(self, datadir, tmpcwd, monkeypatch, requests_mock,
                         invoker):
        monkeypatch.chdir('/var')
        col_id = 'col11405'
        col_version = '1.2'
        col_uuid = 'b699648f-405b-429f-bf11-37bad4246e7c'
        col_hash = '{}@{}'.format(col_uuid, '2.1')
        base_url = 'https://archive.cnx.org'
        metadata_url = '{}/content/{}/{}'.format(base_url, col_id, col_version)
        extras_url = '{}/extras/{}'.format(base_url, col_hash)

        # Register the data urls
        for fname, url in (('contents.json', metadata_url),
                           ('extras.json', extras_url),
                           ):
            register_data_file(requests_mock, datadir, fname, url)

        # Register the resources
        resdir = datadir / 'resources'
        for res in resdir.glob('*'):
            url = '{}/resources/{}'.format(base_url, res.relative_to(resdir))
            register_data_file(requests_mock, resdir, res, url)

        # Register contents
        condir = datadir / 'contents'
        for con in condir.glob('*'):
            url = '{}/contents/{}'.format(base_url, con.relative_to(condir))
            register_data_file(requests_mock, condir, con, url)

        # Register subcollection/chapter as 404
        register_404(requests_mock,
                     'https://archive.cnx.org/contents/'
                     '8ddfc8de-5164-5828-9fed-d0ed17edb489@2.1')

        outdir = tmpcwd / '{}_1.{}'.format(col_id, '2.1')
        from nebu.cli.main import cli
        args = ['get', '-d', str(outdir), 'test-env', col_id, col_version]
        result = invoker(cli, args)

        assert result.exit_code == 0

        outdir = tmpcwd / '{}_1.{}'.format(col_id, '2.1')
        expected = datadir / 'collection'

        def _rel(p, b):
            return p.relative_to(b)

        relative_dir = map(partial(_rel, b=outdir), pathlib_walk(outdir))
        relative_expected = map(partial(_rel, b=expected),
                                pathlib_walk(expected))
        assert sorted(relative_dir) == sorted(relative_expected)

    def test_book_tree(self, datadir, tmpcwd, requests_mock, invoker):
        col_id = 'col11405'
        col_version = '1.2'
        col_uuid = 'b699648f-405b-429f-bf11-37bad4246e7c'
        col_hash = '{}@{}'.format(col_uuid, '2.1')
        base_url = 'https://archive.cnx.org'
        metadata_url = '{}/content/{}/{}'.format(base_url, col_id, col_version)
        extras_url = '{}/extras/{}'.format(base_url, col_hash)

        # Register the data urls
        for fname, url in (('contents.json', metadata_url),
                           ('extras.json', extras_url),
                           ):
            register_data_file(requests_mock, datadir, fname, url)

        # Register the resources
        resdir = datadir / 'resources'
        for res in resdir.glob('*'):
            url = '{}/resources/{}'.format(base_url, res.relative_to(resdir))
            register_data_file(requests_mock, resdir, res, url)

        # Register contents
        condir = datadir / 'contents'
        for con in condir.glob('*'):
            url = '{}/contents/{}'.format(base_url, con.relative_to(condir))
            register_data_file(requests_mock, condir, con, url)

        # Register subcollection/chapter as 404
        register_404(requests_mock,
                     'https://archive.cnx.org/contents/'
                     '8ddfc8de-5164-5828-9fed-d0ed17edb489@2.1')

        from nebu.cli.main import cli
        args = ['get', '-t', 'test-env', col_id, col_version]
        result = invoker(cli, args)

        assert result.exit_code == 0

        dir = tmpcwd / '{}_1.{}'.format(col_id, '2.1')
        expected = datadir / 'book_tree'

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

        # Register the data urls
        for fname, url in (('contents_old.json', metadata_url),
                           ('extras_old.json', extras_url),
                           ('extras.json', latest_url),
                           ):
            register_data_file(requests_mock, datadir, fname, url)

        # Register the resources
        resdir = datadir / 'resources'
        for res in resdir.glob('*'):
            url = '{}/resources/{}'.format(base_url, res.relative_to(resdir))
            register_data_file(requests_mock, resdir, res, url)

        # Register contents
        condir = datadir / 'contents'
        for con in condir.glob('*'):
            url = '{}/contents/{}'.format(base_url, con.relative_to(condir))
            register_data_file(requests_mock, condir, con, url)

        # patch input to return 'y'
        with monkeypatch.context() as m:
            m.setattr('builtins.input', lambda x: "y")
            from nebu.cli.main import cli
            args = ['get', 'test-env', '-d', 'mydir', col_id, col_version]
            result = invoker(cli, args)

        assert result.exit_code == 0

        dir = tmpcwd / 'mydir'
        expected = datadir / 'collection_old'

        def _rel(p, b):
            return p.relative_to(b)

        relative_dir = map(partial(_rel, b=dir), pathlib_walk(dir))
        relative_expected = map(partial(_rel, b=expected),
                                pathlib_walk(expected))
        assert sorted(relative_dir) == sorted(relative_expected)

    def test_not_latest_tree(self, datadir, tmpcwd, requests_mock,
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
                           ('extras.json', latest_url),
                           ):
            register_data_file(requests_mock, datadir, fname, url)

        # Register the resources
        resdir = datadir / 'resources'
        for res in resdir.glob('*'):
            url = '{}/resources/{}'.format(base_url, res.relative_to(resdir))
            register_data_file(requests_mock, resdir, res, url)

        # Register contents
        condir = datadir / 'contents'
        for con in condir.glob('*'):
            url = '{}/contents/{}'.format(base_url, con.relative_to(condir))
            register_data_file(requests_mock, condir, con, url)

        # patch input to return 'y'
        with monkeypatch.context() as m:
            m.setattr('builtins.input', lambda x: "y")
            from nebu.cli.main import cli
            args = ['get', 'test-env', '-t',
                    '-d', 'mydir', col_id, col_version]
            result = invoker(cli, args)

        assert result.exit_code == 0

        dir = tmpcwd / 'mydir'
        expected = datadir / 'book_tree_old'

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

        # patch input to return 'n'
        with monkeypatch.context() as m:
            m.setattr('builtins.input', lambda x: "n")
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

        # Register the data urls
        for fname, url in (('contents.json', metadata_url),
                           ('extras.json', extras_url),
                           ):
            register_data_file(requests_mock, datadir, fname, url)

        # Register the resources
        resdir = datadir / 'resources'
        for res in resdir.glob('*'):
            url = '{}/resources/{}'.format(base_url, res.relative_to(resdir))
            register_data_file(requests_mock, resdir, res, url)

        # Register contents
        condir = datadir / 'contents'
        for con in condir.glob('*'):
            url = '{}/contents/{}'.format(base_url, con.relative_to(condir))
            register_data_file(requests_mock, condir, con, url)

        # Register subcollection/chapter as 404
        register_404(requests_mock,
                     'https://archive.cnx.org/contents/'
                     '8ddfc8de-5164-5828-9fed-d0ed17edb489@2.1')

        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id, col_version]
        result = invoker(cli, args)

        assert result.exit_code == 0

        dir = tmpcwd / '{}_1.{}'.format(col_id, '2.1')
        expected = datadir / 'collection'

        def _rel(p, b):
            return p.relative_to(b)

        relative_dir = map(partial(_rel, b=dir), pathlib_walk(dir))
        relative_expected = map(partial(_rel, b=expected),
                                pathlib_walk(expected))
        assert sorted(relative_dir) == sorted(relative_expected)

    def test_with_existing_output_dir(self, tmpcwd, invoker, requests_mock,
                                      datadir):
        col_id = 'col00000'
        col_version = '2.1'
        base_url = 'https://archive.cnx.org'
        url = '{}/content/{}/{}'.format(base_url, col_id, col_version)

        # Register the metadata url
        register_data_file(requests_mock, datadir, 'contents.json', url)

        expected_output_dir = '{}_1.{}'.format(col_id, col_version)
        (tmpcwd / expected_output_dir).mkdir()

        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id, col_version]
        result = invoker(cli, args)

        assert result.exit_code == 3

        assert 'directory already exists:' in result.output

    def test_failed_request_omitting_version(self, invoker):
        col_id = 'col00000'

        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id]
        result = invoker(cli, args)

        assert result.exit_code == 2

        assert 'Missing argument "COL_VERSION"' in result.output

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
