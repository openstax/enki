from pathlib import Path

import pytest


class TestConfigAtomCmd:

    @pytest.fixture(autouse=True)
    def setup(self, tmpdir, monkeypatch):
        import pkg_resources
        self.resource_filename = 'foo/bar.rng'
        monkeypatch.setattr(pkg_resources, 'resource_filename',
                            lambda *a: self.resource_filename)
        self.tmpdir = Path(str(tmpdir))
        monkeypatch.setattr(Path, 'home', lambda: self.tmpdir)

    def check(self, result):
        assert result.exit_code == 0
        assert 'Wrote ' in result.output
        assert '/.atom/config.cson' in result.output

        filepath = self.tmpdir / '.atom/config.cson'
        with filepath.open('r') as fb:
            assert self.resource_filename in fb.read()

    def test(self, invoker):
        from nebu.cli.main import cli
        args = ['config-atom', '--yes']
        result = invoker(cli, args)
        self.check(result)

    def test_with_exiting_config(self, monkeypatch, invoker):
        filepath = self.tmpdir / '.atom/config.cson'
        backup_filepath = filepath.parent / (filepath.name + '.bak')
        filepath.parent.mkdir()
        with filepath.open('w') as fb:
            fb.write('baz')

        from nebu.cli.main import cli
        args = ['config-atom', '--yes']
        result = invoker(cli, args)
        self.check(result)

        # Check for backup file creation
        assert 'Wrote backup to ' in result.output
        with backup_filepath.open('r') as fb:
            assert 'baz' in fb.read()

    def test_with_exiting_config_and_backup(self, monkeypatch, invoker):
        filepath = self.tmpdir / '.atom/config.cson'
        backup_filepath = filepath.parent / (filepath.name + '.bak')
        filepath.parent.mkdir()
        with filepath.open('w') as fb:
            fb.write('baz')
        with backup_filepath.open('w') as fb:
            fb.write('raz')

        from nebu.cli.main import cli
        args = ['config-atom', '--yes']
        result = invoker(cli, args)
        self.check(result)

        # Check for backup file is overwritten
        assert 'Wrote backup to ' in result.output
        with backup_filepath.open('r') as fb:
            assert 'baz' in fb.read()
