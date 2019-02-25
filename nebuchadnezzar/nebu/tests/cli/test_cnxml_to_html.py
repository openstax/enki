import os
from unittest import mock

import pytest


def get_files(directory, filename):
    for root, dirs, files in os.walk(str(directory)):
        if filename in files:
            yield os.path.join(root, filename)


@pytest.fixture
def clear_files(request):
    def _clear_files(directory, filename):
        def cleanup():
            for f in get_files(directory, filename):
                os.unlink(f)

        # make sure files are removed before tests
        cleanup()

        # make sure files are removed after tests
        request.addfinalizer(cleanup)

    return _clear_files


@pytest.fixture
def cnxml_to_full_html(request):
    patcher = mock.patch('nebu.cli.cnxml_to_html.cnxml_to_full_html')
    mock_function = patcher.start()
    mock_function.return_value = '<html><body>transformed html</body></html>'
    request.addfinalizer(patcher.stop)
    return mock_function


class TestCnxmlToHtmlCmd:
    def test(self, datadir, invoker, clear_files, cnxml_to_full_html):
        col_path = datadir / 'collection_no_changes'

        # make sure index.cnxml.html doesn't exist
        clear_files(col_path, 'index.cnxml.html')
        index_cnxml_html = list(get_files(col_path, 'index.cnxml.html'))
        assert index_cnxml_html == []

        from nebu.cli.main import cli
        args = ['cnxml-to-html', str(col_path)]
        result = invoker(cli, args)
        assert result.exit_code == 0

        # make sure the number of index.cnxml.html is the same as index.cnxml
        index_cnxml = list(get_files(col_path, 'index.cnxml'))
        index_cnxml_html = list(get_files(col_path, 'index.cnxml.html'))
        assert len(index_cnxml) == len(index_cnxml_html)
        assert cnxml_to_full_html.call_count == len(index_cnxml)

        # check that the index.cnxml.html is indeed transformed with the mocked
        # cnxml_to_full_html function
        for path in index_cnxml_html:
            with open(path) as f:
                content = f.read()
            assert '<html><body>transformed html</body></html>' == content
