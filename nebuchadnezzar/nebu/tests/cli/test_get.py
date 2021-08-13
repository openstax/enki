from functools import partial
from os import scandir
from pathlib import Path
import traceback
import asyncio
import json
import re
import pytest

from nebu.cli.get import _write_contents
from nebu.cli._common import calculate_sha1


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


def register_data_file_aio(mock_aioresponses, datadir, filename, url):
    datafile = datadir / filename
    content_size = datafile.stat().st_size
    with datafile.open('rb') as fb:
        headers = {'Content-Length': str(content_size)}
        mock_aioresponses.get(
            url,
            body=fb.read(),
            headers=headers,
            repeat=True
        )


def register_404_aio(mock_aioresponses, url):
    mock_aioresponses.get(
        url,
        body='Not Found',
        status=404,
        repeat=True
    )


def register_404(requests_mock, url):
    requests_mock.get(
        url,
        text='Not Found',
        status_code=404,
    )


def debug_result_exception(result):
    if result.exception:
        traceback.print_tb(result.exception.__traceback__)
        print(type(result.exception))
        print(str(result.exception))
        print(result.stdout_bytes.decode('utf8'))


# https://github.com/openstax/cnx/issues/291
def test_utf8_content(tmpdir,
                      requests_mock,
                      mock_aioresponses,
                      datadir):
    # This test is terribly written, but it's because the code...
    out_dir = Path(str(tmpdir))
    base_url = 'https://archive.cnx.org'
    node = {'id': 'foo'}
    legacy_id = 'm68234'
    resource_id = '9d85db7'

    # Mock the request for the json data
    data = {
        'legacy_id': legacy_id,
        'mediaType': 'application/vnd.org.cnx.module',
        'resources': [
            {"filename": "index.cnxml.html",
             "id": "9d575fa06166c707dcf4da7a91f45b89312220ce",
             "media_type": "text/html"
             },
            {"filename": "index.cnxml",
             # "id": "9d85db72dd58143a57da0e29abae3c76a55a09f3",
             "id": resource_id,
             "media_type": "application/octet-stream"
             },
        ],
    }
    url = '{}/contents/{}'.format(base_url, node['id'])
    mock_aioresponses.get(url, payload=data)

    # Mock the request for the cnxml resource
    with (datadir / 'unicode.cnxml').open('rb') as fb:
        cnxml = fb.read()
    url = '{}/resources/{}'.format(base_url, resource_id)
    mock_aioresponses.get(url, body=cnxml)

    # Call the target
    loop = asyncio.get_event_loop()
    coro = _write_contents(node, base_url, out_dir)
    loop.run_until_complete(coro)

    # Verify the content is as specified
    with (datadir / 'unicode.cnxml').open('rb') as fb:
        expected = fb.read()
    with (out_dir / legacy_id / 'index.cnxml').open('rb') as fb:
        assert fb.read() == expected


class TestGetCmd:

    def test_general(self,
                     datadir,
                     tmpcwd,
                     requests_mock,
                     mock_aioresponses,
                     invoker):
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
            register_data_file_aio(mock_aioresponses, resdir, res, url)

        # Register contents
        condir = datadir / 'contents'
        for con in condir.glob('*'):
            url = '{}/contents/{}'.format(base_url, con.relative_to(condir))
            register_data_file(requests_mock, condir, con, url)
            register_data_file_aio(mock_aioresponses, condir, con, url)

        # Register subcollection/chapter as 404
        register_404_aio(mock_aioresponses,
                         'https://archive.cnx.org/contents/'
                         '8ddfc8de-5164-5828-9fed-d0ed17edb489@2.1')

        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id, col_version]
        result = invoker(cli, args)

        debug_result_exception(result)
        assert result.exit_code == 0

        dir = tmpcwd / '{}_1.{}'.format(col_id, '2.1')
        expected = datadir / 'collection'

        def _rel(p, b):
            return p.relative_to(b)

        relative_dir = map(partial(_rel, b=dir), pathlib_walk(dir))
        relative_expected = map(partial(_rel, b=expected),
                                pathlib_walk(expected))
        assert sorted(relative_dir) == sorted(relative_expected)

    @pytest.mark.parametrize('environment',
                             ['qa', 'qa.cnx.org', 'https://qa.cnx.org'])
    def test_with_fallback_archive(self,
                                   datadir,
                                   tmpcwd,
                                   requests_mock,
                                   mock_aioresponses,
                                   invoker,
                                   environment):
        col_id = 'col11405'
        col_version = '1.2'
        col_uuid = 'b699648f-405b-429f-bf11-37bad4246e7c'
        col_hash = '{}@{}'.format(col_uuid, '2.1')
        base_url = 'https://archive-qa.cnx.org'
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
            register_data_file_aio(mock_aioresponses, resdir, res, url)

        # Register contents
        condir = datadir / 'contents'
        for con in condir.glob('*'):
            url = '{}/contents/{}'.format(base_url, con.relative_to(condir))
            register_data_file(requests_mock, condir, con, url)
            register_data_file_aio(mock_aioresponses, condir, con, url)

        # Register subcollection/chapter as 404
        register_404_aio(mock_aioresponses,
                         'https://archive-qa.cnx.org/contents/'
                         '8ddfc8de-5164-5828-9fed-d0ed17edb489@2.1')

        from nebu.cli.main import cli
        args = ['get', environment, col_id, col_version]
        result = invoker(cli, args)

        debug_result_exception(result)
        assert result.exit_code == 0

        dir = tmpcwd / '{}_1.{}'.format(col_id, '2.1')
        expected = datadir / 'collection'

        def _rel(p, b):
            return p.relative_to(b)

        relative_dir = map(partial(_rel, b=dir), pathlib_walk(dir))
        relative_expected = map(partial(_rel, b=expected),
                                pathlib_walk(expected))
        assert sorted(relative_dir) == sorted(relative_expected)

    def test_with_archive_fqdn(self,
                               datadir,
                               tmpcwd,
                               requests_mock,
                               mock_aioresponses,
                               invoker):
        col_id = 'col11405'
        col_version = '1.2'
        col_uuid = 'b699648f-405b-429f-bf11-37bad4246e7c'
        col_hash = '{}@{}'.format(col_uuid, '2.1')
        base_url = 'https://archive.local.cnx.org'
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
            register_data_file_aio(mock_aioresponses, resdir, res, url)

        # Register contents
        condir = datadir / 'contents'
        for con in condir.glob('*'):
            url = '{}/contents/{}'.format(base_url, con.relative_to(condir))
            register_data_file(requests_mock, condir, con, url)
            register_data_file_aio(mock_aioresponses, condir, con, url)

        # Register subcollection/chapter as 404
        register_404_aio(mock_aioresponses,
                         'https://archive.local.cnx.org/contents/'
                         '8ddfc8de-5164-5828-9fed-d0ed17edb489@2.1')

        from nebu.cli.main import cli
        args = ['get', 'random-env', '--archive', 'archive.local.cnx.org',
                col_id, col_version]
        result = invoker(cli, args)

        debug_result_exception(result)
        assert result.exit_code == 0

        dir = tmpcwd / '{}_1.{}'.format(col_id, '2.1')
        expected = datadir / 'collection'

        def _rel(p, b):
            return p.relative_to(b)

        relative_dir = map(partial(_rel, b=dir), pathlib_walk(dir))
        relative_expected = map(partial(_rel, b=expected),
                                pathlib_walk(expected))
        assert sorted(relative_dir) == sorted(relative_expected)

    def test_with_archive_fqdn_with_protocol(self,
                                             datadir,
                                             tmpcwd,
                                             requests_mock,
                                             mock_aioresponses,
                                             invoker):
        col_id = 'col11405'
        col_version = '1.2'
        col_uuid = 'b699648f-405b-429f-bf11-37bad4246e7c'
        col_hash = '{}@{}'.format(col_uuid, '2.1')
        base_url = 'http://archive.local.cnx.org'
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
            register_data_file_aio(mock_aioresponses, resdir, res, url)

        # Register contents
        condir = datadir / 'contents'
        for con in condir.glob('*'):
            url = '{}/contents/{}'.format(base_url, con.relative_to(condir))
            register_data_file(requests_mock, condir, con, url)
            register_data_file_aio(mock_aioresponses, condir, con, url)

        # Register subcollection/chapter as 404
        register_404_aio(mock_aioresponses,
                         'http://archive.local.cnx.org/contents/'
                         '8ddfc8de-5164-5828-9fed-d0ed17edb489@2.1')

        from nebu.cli.main import cli
        args = ['get', 'random-env', '--archive',
                'http://archive.local.cnx.org', col_id, col_version]
        result = invoker(cli, args)

        debug_result_exception(result)
        assert result.exit_code == 0

        dir = tmpcwd / '{}_1.{}'.format(col_id, '2.1')
        expected = datadir / 'collection'

        def _rel(p, b):
            return p.relative_to(b)

        relative_dir = map(partial(_rel, b=dir), pathlib_walk(dir))
        relative_expected = map(partial(_rel, b=expected),
                                pathlib_walk(expected))
        assert sorted(relative_dir) == sorted(relative_expected)

    def test_with_resources(self,
                            datadir,
                            tmpcwd,
                            requests_mock,
                            mock_aioresponses,
                            invoker):
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
            register_data_file_aio(mock_aioresponses, resdir, res, url)

        # Register contents
        condir = datadir / 'contents'
        for con in condir.glob('*'):
            url = '{}/contents/{}'.format(base_url, con.relative_to(condir))
            register_data_file(requests_mock, condir, con, url)
            register_data_file_aio(mock_aioresponses, condir, con, url)

        # Register subcollection/chapter as 404
        register_404_aio(mock_aioresponses,
                         'https://archive.cnx.org/contents/'
                         '8ddfc8de-5164-5828-9fed-d0ed17edb489@2.1')

        from nebu.cli.main import cli
        args = ['get', '--get-resources', 'test-env', col_id, col_version]
        result = invoker(cli, args)

        debug_result_exception(result)
        assert result.exit_code == 0

        dir = tmpcwd / '{}_1.{}'.format(col_id, '2.1')
        expected = datadir / 'collection_get_resources'

        def _rel(p, b):
            return p.relative_to(b)

        relative_dir = map(partial(_rel, b=dir), pathlib_walk(dir))
        relative_expected = map(partial(_rel, b=expected),
                                pathlib_walk(expected))
        assert sorted(relative_dir) == sorted(relative_expected)

    def test_with_resources_limit_1_request(self,
                                            datadir,
                                            tmpcwd,
                                            requests_mock,
                                            mock_aioresponses,
                                            invoker):
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
            register_data_file_aio(mock_aioresponses, resdir, res, url)

        # Register contents
        condir = datadir / 'contents'
        for con in condir.glob('*'):
            url = '{}/contents/{}'.format(base_url, con.relative_to(condir))
            register_data_file(requests_mock, condir, con, url)
            register_data_file_aio(mock_aioresponses, condir, con, url)

        # Register subcollection/chapter as 404
        register_404_aio(mock_aioresponses,
                         'https://archive.cnx.org/contents/'
                         '8ddfc8de-5164-5828-9fed-d0ed17edb489@2.1')

        from nebu.cli.main import cli
        args = ['get', '-l', 1, '--get-resources', 'test-env',
                col_id, col_version]
        result = invoker(cli, args)

        debug_result_exception(result)
        assert result.exit_code == 0

        dir = tmpcwd / '{}_1.{}'.format(col_id, '2.1')
        expected = datadir / 'collection_get_resources'

        def _rel(p, b):
            return p.relative_to(b)

        relative_dir = map(partial(_rel, b=dir), pathlib_walk(dir))
        relative_expected = map(partial(_rel, b=expected),
                                pathlib_walk(expected))
        assert sorted(relative_dir) == sorted(relative_expected)

    def test_metadata(self,
                      datadir,
                      tmpcwd,
                      requests_mock,
                      mock_aioresponses,
                      invoker):
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
            register_data_file_aio(mock_aioresponses, resdir, res, url)

        # Register contents
        condir = datadir / 'contents'
        for con in condir.glob('*'):
            url = '{}/contents/{}'.format(base_url, con.relative_to(condir))
            register_data_file(requests_mock, condir, con, url)
            register_data_file_aio(mock_aioresponses, condir, con, url)

        # Register subcollection/chapter as 404
        register_404_aio(mock_aioresponses,
                         'https://archive.cnx.org/contents/'
                         '8ddfc8de-5164-5828-9fed-d0ed17edb489@2.1')

        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id, col_version]
        result = invoker(cli, args)

        debug_result_exception(result)
        assert result.exit_code == 0

        dir = tmpcwd / '{}_1.{}'.format(col_id, '2.1')
        expected = datadir / 'collection'

        for metadata_json in Path(expected).glob('**/metadata.json'):
            metadata_file = dir / metadata_json.relative_to(expected)
            assert metadata_file.exists()

            with open(metadata_file) as json_data:
                metadata_received = json.load(json_data)
            with open(metadata_json) as json_data:
                metadata_expected = json.load(json_data)
            assert metadata_received == metadata_expected

    def test_three_part_vers(self,
                             datadir,
                             tmpcwd,
                             monkeypatch,
                             requests_mock,
                             mock_aioresponses,
                             invoker):
        col_id = 'col11405'
        col_version = '1.1'
        trip_ver = '1.1.1'
        col_uuid = 'b699648f-405b-429f-bf11-37bad4246e7c'
        col_hash = '{}@{}'.format(col_uuid, '1.4')
        base_url = 'https://archive.cnx.org'
        metadata_url = '{}/content/{}/{}'.format(base_url, col_id, col_version)
        extras_url = '{}/extras/{}'.format(base_url, col_hash)
        extra_extras_url = '{}/extras/{}@{}'.format(base_url, col_uuid, '1.1')

        # Register the data urls
        for fname, url in (('contents_1.4.json', metadata_url),
                           ('extras_1.4.json', extras_url),
                           ('extras_old.json', extra_extras_url),
                           ):
            register_data_file(requests_mock, datadir, fname, url)

        # Register the resources
        resdir = datadir / 'resources'
        for res in resdir.glob('*'):
            url = '{}/resources/{}'.format(base_url, res.relative_to(resdir))
            register_data_file_aio(mock_aioresponses, resdir, res, url)

        # Register contents
        condir = datadir / 'contents'
        for con in condir.glob('*'):
            url = '{}/contents/{}'.format(base_url, con.relative_to(condir))
            register_data_file(requests_mock, condir, con, url)
            register_data_file_aio(mock_aioresponses, condir, con, url)

        # Register subcollection/chapter as 404
        register_404_aio(mock_aioresponses,
                         'https://archive.cnx.org/contents/'
                         '8ddfc8de-5164-5828-9fed-d0ed17edb489@1.1')

        # patch input to return 'y' - getting not-head
        with monkeypatch.context() as m:
            m.setattr('builtins.input', lambda x: "y")
            from nebu.cli.main import cli
            args = ['get', 'test-env', col_id, trip_ver]
            result = invoker(cli, args)

        debug_result_exception(result)
        assert result.exit_code == 0

        dir = tmpcwd / '{}_1.{}'.format(col_id, '1.1')
        expected = datadir / 'collection'

        def _rel(p, b):
            return p.relative_to(b)

        relative_dir = map(partial(_rel, b=dir), pathlib_walk(dir))
        relative_expected = map(partial(_rel, b=expected),
                                pathlib_walk(expected))
        assert sorted(relative_dir) == sorted(relative_expected)

    def test_three_part_bad_ver(self,
                                datadir,
                                tmpcwd,
                                monkeypatch,
                                requests_mock,
                                mock_aioresponses,
                                invoker):
        col_id = 'col11405'
        col_version = '1.1'
        trip_ver = '1.1.5'
        col_uuid = 'b699648f-405b-429f-bf11-37bad4246e7c'
        col_hash = '{}@{}'.format(col_uuid, '1.4')
        base_url = 'https://archive.cnx.org'
        metadata_url = '{}/content/{}/{}'.format(base_url, col_id, col_version)
        extras_url = '{}/extras/{}'.format(base_url, col_hash)
        extra_extras_url = '{}/extras/{}@{}'.format(base_url, col_uuid, '1.1')

        # Register the data urls
        for fname, url in (('contents_1.4.json', metadata_url),
                           ('extras_1.4.json', extras_url),
                           ('extras_old.json', extra_extras_url),
                           ):
            register_data_file(requests_mock, datadir, fname, url)

        # Register bad version as 404
        register_404(requests_mock,
                     'https://archive.cnx.org/contents/'
                     'b699648f-405b-429f-bf11-37bad4246e7c@1.5')

        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id, trip_ver]
        result = invoker(cli, args)

        assert result.exit_code == 4

        msg = "content unavailable for '{}/{}'".format(col_id, trip_ver)
        assert msg in result.output

    def test_outside_cwd(self,
                         datadir,
                         tmpcwd,
                         monkeypatch,
                         requests_mock,
                         mock_aioresponses,
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
            register_data_file_aio(mock_aioresponses, resdir, res, url)

        # Register contents
        condir = datadir / 'contents'
        for con in condir.glob('*'):
            url = '{}/contents/{}'.format(base_url, con.relative_to(condir))
            register_data_file(requests_mock, condir, con, url)
            register_data_file_aio(mock_aioresponses, condir, con, url)

        # Register subcollection/chapter as 404
        register_404_aio(mock_aioresponses,
                         'https://archive.cnx.org/contents/'
                         '8ddfc8de-5164-5828-9fed-d0ed17edb489@2.1')

        outdir = tmpcwd / '{}_1.{}'.format(col_id, '2.1')
        from nebu.cli.main import cli
        args = ['get', '-d', str(outdir), 'test-env', col_id, col_version]
        result = invoker(cli, args)

        debug_result_exception(result)
        assert result.exit_code == 0

        outdir = tmpcwd / '{}_1.{}'.format(col_id, '2.1')
        expected = datadir / 'collection'

        def _rel(p, b):
            return p.relative_to(b)

        relative_dir = map(partial(_rel, b=outdir), pathlib_walk(outdir))
        relative_expected = map(partial(_rel, b=expected),
                                pathlib_walk(expected))
        assert sorted(relative_dir) == sorted(relative_expected)

    def test_book_tree(self,
                       datadir,
                       tmpcwd,
                       requests_mock,
                       mock_aioresponses,
                       invoker):
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
            register_data_file_aio(mock_aioresponses, resdir, res, url)

        # Register contents
        condir = datadir / 'contents'
        for con in condir.glob('*'):
            url = '{}/contents/{}'.format(base_url, con.relative_to(condir))
            register_data_file(requests_mock, condir, con, url)
            register_data_file_aio(mock_aioresponses, condir, con, url)

        # Register subcollection/chapter as 404
        register_404_aio(mock_aioresponses,
                         'https://archive.cnx.org/contents/'
                         '8ddfc8de-5164-5828-9fed-d0ed17edb489@2.1')

        from nebu.cli.main import cli
        args = ['get', '-t', 'test-env', col_id, col_version]
        result = invoker(cli, args)

        debug_result_exception(result)
        assert result.exit_code == 0

        dir = tmpcwd / '{}_1.{}'.format(col_id, '2.1')
        expected = datadir / 'book_tree'

        def _rel(p, b):
            return p.relative_to(b)

        relative_dir = map(partial(_rel, b=dir), pathlib_walk(dir))
        relative_expected = map(partial(_rel, b=expected),
                                pathlib_walk(expected))
        assert sorted(relative_dir) == sorted(relative_expected)

    def test_not_latest(self,
                        datadir,
                        tmpcwd,
                        requests_mock,
                        mock_aioresponses,
                        monkeypatch,
                        invoker):
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
            register_data_file_aio(mock_aioresponses, resdir, res, url)

        # Register contents
        condir = datadir / 'contents'
        for con in condir.glob('*'):
            url = '{}/contents/{}'.format(base_url, con.relative_to(condir))
            register_data_file(requests_mock, condir, con, url)
            register_data_file_aio(mock_aioresponses, condir, con, url)

        # patch input to return 'y'
        with monkeypatch.context() as m:
            m.setattr('builtins.input', lambda x: "y")
            from nebu.cli.main import cli
            args = ['get', 'test-env', '-d', 'mydir', col_id, col_version]
            result = invoker(cli, args)

        debug_result_exception(result)
        assert result.exit_code == 0

        dir = tmpcwd / 'mydir'
        expected = datadir / 'collection_old'

        def _rel(p, b):
            return p.relative_to(b)

        relative_dir = map(partial(_rel, b=dir), pathlib_walk(dir))
        relative_expected = map(partial(_rel, b=expected),
                                pathlib_walk(expected))
        assert sorted(relative_dir) == sorted(relative_expected)

    def test_not_latest_tree(self,
                             datadir,
                             tmpcwd,
                             requests_mock,
                             mock_aioresponses,
                             monkeypatch,
                             invoker):
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
            register_data_file_aio(mock_aioresponses, resdir, res, url)

        # Register contents
        condir = datadir / 'contents'
        for con in condir.glob('*'):
            url = '{}/contents/{}'.format(base_url, con.relative_to(condir))
            register_data_file(requests_mock, condir, con, url)
            register_data_file_aio(mock_aioresponses, condir, con, url)

        # patch input to return 'y'
        with monkeypatch.context() as m:
            m.setattr('builtins.input', lambda x: "y")
            from nebu.cli.main import cli
            args = ['get', 'test-env', '-t',
                    '-d', 'mydir', col_id, col_version]
            result = invoker(cli, args)

        debug_result_exception(result)
        assert result.exit_code == 0

        dir = tmpcwd / 'mydir'
        expected = datadir / 'book_tree_old'

        def _rel(p, b):
            return p.relative_to(b)

        relative_dir = map(partial(_rel, b=dir), pathlib_walk(dir))
        relative_expected = map(partial(_rel, b=expected),
                                pathlib_walk(expected))
        assert sorted(relative_dir) == sorted(relative_expected)

    def test_not_latest_abort(self,
                              datadir,
                              tmpcwd,
                              requests_mock,
                              mock_aioresponses,
                              monkeypatch,
                              invoker):
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

    def test_latest(self,
                    datadir,
                    tmpcwd,
                    requests_mock,
                    mock_aioresponses,
                    invoker):
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
            register_data_file_aio(mock_aioresponses, resdir, res, url)

        # Register contents
        condir = datadir / 'contents'
        for con in condir.glob('*'):
            url = '{}/contents/{}'.format(base_url, con.relative_to(condir))
            register_data_file(requests_mock, condir, con, url)
            register_data_file_aio(mock_aioresponses, condir, con, url)

        # Register subcollection/chapter as 404
        register_404_aio(mock_aioresponses,
                         'https://archive.cnx.org/contents/'
                         '8ddfc8de-5164-5828-9fed-d0ed17edb489@2.1')

        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id, col_version]
        result = invoker(cli, args)

        debug_result_exception(result)
        assert result.exit_code == 0

        dir = tmpcwd / '{}_1.{}'.format(col_id, '2.1')
        expected = datadir / 'collection'

        def _rel(p, b):
            return p.relative_to(b)

        relative_dir = map(partial(_rel, b=dir), pathlib_walk(dir))
        relative_expected = map(partial(_rel, b=expected),
                                pathlib_walk(expected))
        assert sorted(relative_dir) == sorted(relative_expected)

    def test_with_existing_output_dir(self,
                                      tmpcwd,
                                      invoker,
                                      requests_mock,
                                      mock_aioresponses,
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

        expected_output = re.compile('Missing argument ["\']COL_VERSION["\']')
        assert expected_output.search(result.output)

    def test_failed_request_using_version(self,
                                          requests_mock,
                                          mock_aioresponses,
                                          invoker):
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

    def test_failed_request_no_raw(self,
                                   datadir,
                                   requests_mock,
                                   mock_aioresponses,
                                   invoker):
        col_id = 'col11405'
        col_version = 'latest'
        col_uuid = 'b699648f-405b-429f-bf11-37bad4246e7c'
        col_hash = '{}@{}'.format(col_uuid, '2.1')
        base_url = 'https://archive.cnx.org'
        metadata_url = '{}/content/{}/{}'.format(base_url, col_id, col_version)
        extras_url = '{}/extras/{}'.format(base_url, col_hash)
        contents_url = '{}/contents/{}'.format(base_url, col_hash)
        raw_url = '{}/contents/{}?as_collated=False'.format(base_url, col_hash)

        # Register the data urls
        for fname, url in (('contents.json', contents_url),
                           ('extras.json', extras_url),
                           ):
            register_data_file(requests_mock, datadir, fname, url)

        requests_mock.get(metadata_url,
                          status_code=301,
                          headers={'location': contents_url})

        register_404(requests_mock, raw_url)

        from nebu.cli.main import cli
        args = ['get', 'test-env', col_id, col_version]
        result = invoker(cli, args)

        assert result.exit_code == 4

        msg = "content unavailable for '{}/{}'".format(col_id, col_version)
        assert msg in result.output

    def test_sha1_with_non_utf8_content(self,
                                        requests_mock,
                                        mock_aioresponses,
                                        datadir):
        """At one point in time, modules which contained unicode characters
         (used to) get ascii-encoded on dowload, and then we fixed it, but
        this became an issue when detecting files that have changed because
        the sha1 hash differs. This code tests that the hashing is done after
        encoding.

        See: https://github.com/openstax/cnx/issues/273
        """
        out_dir = Path(str(datadir))
        base_url = 'https://archive.cnx.org'
        node = {'id': 'foo'}
        legacy_id = 'm68234'
        resource_id = '9d85db7'

        # Mock the request for the json data
        metadata = {
            'legacy_id': legacy_id,
            'mediaType': 'application/vnd.org.cnx.module',
            'resources': [
                {
                    "filename": "index.cnxml",
                    "id": resource_id,
                    "media_type": "application/octet-stream"
                },
            ],
        }
        url = '{}/contents/{}'.format(base_url, node['id'])
        mock_aioresponses.get(url, payload=metadata)

        with (datadir / 'mod_ascii_encoded.cnxml').open('rb') as fb:
            mod_ascii_encoded = fb.read()

        url = '{}/resources/{}'.format(base_url, resource_id)
        # Downloads the ascii-encoded module
        mock_aioresponses.get(url, body=mod_ascii_encoded)

        # Call the target
        loop = asyncio.get_event_loop()
        coro = _write_contents(node, base_url, out_dir)
        loop.run_until_complete(coro)

        """ Verify the sha1 is as expected """
        downloaded_hash = get_sha1s_dict(out_dir / legacy_id)["index.cnxml"]
        expected_utf8_encoded_hash = calculate_sha1(
            datadir / "mod_utf8_encoded.cnxml"
        )

        # Expect the stored hash to be the one for the utf-8 encoded module
        assert downloaded_hash == expected_utf8_encoded_hash

        # clean up
        import shutil
        shutil.rmtree(str(datadir / legacy_id))


class TestHeadCmd:
    def test_general(self,
                     datadir,
                     tmpcwd,
                     requests_mock,
                     invoker):
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

        from nebu.cli.main import cli
        args = ['head', 'test-env', col_id]
        result = invoker(cli, args)

        debug_result_exception(result)
        assert result.exit_code == 0
        assert result.stdout == '2.1\n'

    @pytest.mark.parametrize('environment',
                             ['qa', 'qa.cnx.org', 'https://qa.cnx.org'])
    def test_with_fallback_archive(self,
                                   datadir,
                                   tmpcwd,
                                   requests_mock,
                                   mock_aioresponses,
                                   invoker,
                                   environment):
        col_id = 'col11405'
        col_version = 'latest'
        col_uuid = 'b699648f-405b-429f-bf11-37bad4246e7c'
        col_hash = '{}@{}'.format(col_uuid, '2.1')
        base_url = 'https://archive-qa.cnx.org'
        metadata_url = '{}/content/{}/{}'.format(base_url, col_id, col_version)
        extras_url = '{}/extras/{}'.format(base_url, col_hash)

        # Register the data urls
        for fname, url in (('contents.json', metadata_url),
                           ('extras.json', extras_url),
                           ):
            register_data_file(requests_mock, datadir, fname, url)

        from nebu.cli.main import cli
        args = ['head', environment, col_id]
        result = invoker(cli, args)

        debug_result_exception(result)
        assert result.exit_code == 0
        assert result.stdout == '2.1\n'


def get_sha1s_dict(path):
    """Returns a dict of sha1-s by filename"""
    try:
        with (path / '.sha1sum').open('r') as sha_file:
            return {line.split('  ')[1].strip(): line.split('  ')[0].strip()
                    for line in sha_file if not line.startswith('#')}
    except FileNotFoundError:
        return {}
