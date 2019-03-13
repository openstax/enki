from pathlib import Path

import pytest

from nebu.utils import relative_path


def _mkdir(p):
    try:
        p.mkdir()
    except FileNotFoundError:
        _mkdir(p.parent)
        p.mkdir()


@pytest.fixture
def test_dirs(tmp_path):
    dirs = [
        tmp_path / 'foo' / 'aaa' / '000',
        tmp_path / 'bar' / 'bbb' / '111',
        tmp_path / 'baz' / 'ccc' / '222',
    ]
    for d in dirs:
        _mkdir(d)
    return dirs


@pytest.mark.usefixtures('test_dirs')
class TestRelativePath(object):
    # These test ``p`` relative to ``s``

    def test_sibling(self, tmp_path):
        p = tmp_path / 'foo'
        s = tmp_path / 'bar'
        result = relative_path(p, s)
        assert result == Path('../foo')

    def test_child(self, tmp_path):
        p = tmp_path / 'baz' / 'bbb' / '111'
        s = tmp_path
        result = relative_path(p, s)
        assert result == Path('baz/bbb/111')

    def test_distant_siblings(self, tmp_path):
        p = tmp_path / 'foo' / 'aaa' / '000'
        s = tmp_path / 'bar' / 'bbb' / '111'
        result = relative_path(p, s)
        assert result == Path('../../../foo/aaa/000')
