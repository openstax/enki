from pathlib import Path

import pretend

from nebu.config import (
    INITIAL_DEFAULT_CONFIG,
    discover_settings,
    prepare,
)


TESTING_CONFIG = """\
[settings]

[environ-local]
url = http://localhost:6543

[environ-dev]
url = https://dev.cnx.org
"""


class TestDiscoverSettings:

    def test_home_dir_config_found(self, tmpdir, monkeypatch):
        loc = Path(str(tmpdir / 'config.ini'))
        monkeypatch.setattr('nebu.config.CONFIG_FILE_LOC', loc)
        monkeypatch.setattr('os.environ', {})

        with loc.open('w') as fb:
            fb.write(TESTING_CONFIG)

        settings = discover_settings()

        expected_settings = {
            '_config_file': loc,
            'environs': {
                'dev': {'url': 'https://dev.cnx.org'},
                'local': {'url': 'http://localhost:6543'},
            },
        }
        assert settings == expected_settings

    def test_environ_var_config(self, tmpdir, monkeypatch):
        loc = Path(str(tmpdir / 'config.ini'))
        monkeypatch.setattr('os.environ', {'NEB_CONFIG': str(loc)})

        with loc.open('w') as fb:
            fb.write(TESTING_CONFIG)

        settings = discover_settings()

        expected_settings = {
            '_config_file': loc,
            'environs': {
                'dev': {'url': 'https://dev.cnx.org'},
                'local': {'url': 'http://localhost:6543'},
            },
        }
        assert settings == expected_settings

    def test_missing_config(self, tmpdir, monkeypatch):
        loc = Path(str(tmpdir / 'config.ini'))
        monkeypatch.setattr('nebu.config.CONFIG_FILE_LOC', loc)
        monkeypatch.setattr('os.environ', {})

        settings = discover_settings()

        expected_settings = {
            '_config_file': loc,
            'environs': {
                'dev': {'url': 'https://dev.cnx.org'},
                'qa': {'url': 'https://qa.cnx.org'},
                'staging': {'url': 'https://staging.cnx.org'},
                'prod': {'url': 'https://cnx.org'},
                'content01': {'url': 'https://content01.cnx.org'},
                'content02': {'url': 'https://content02.cnx.org'},
                'content03': {'url': 'https://content03.cnx.org'},
                'content04': {'url': 'https://content04.cnx.org'},
                'content05': {'url': 'https://content05.cnx.org'},
                'staged': {'url': 'https://staged.cnx.org'},
            },
        }
        assert settings == expected_settings

        with loc.open('r') as fb:
            assert fb.read() == INITIAL_DEFAULT_CONFIG

    def test_missing_config_and_parent_directory(self, tmpdir, monkeypatch):
        loc = Path(str(tmpdir)) / '.config' / 'config.ini'
        monkeypatch.setattr('nebu.config.CONFIG_FILE_LOC', loc)
        monkeypatch.setattr('os.environ', {})

        settings = discover_settings()

        expected_settings = {
            '_config_file': loc,
            'environs': {
                'dev': {'url': 'https://dev.cnx.org'},
                'qa': {'url': 'https://qa.cnx.org'},
                'staging': {'url': 'https://staging.cnx.org'},
                'prod': {'url': 'https://cnx.org'},
                'content01': {'url': 'https://content01.cnx.org'},
                'content02': {'url': 'https://content02.cnx.org'},
                'content03': {'url': 'https://content03.cnx.org'},
                'content04': {'url': 'https://content04.cnx.org'},
                'content05': {'url': 'https://content05.cnx.org'},
                'staged': {'url': 'https://staged.cnx.org'},
            },
        }
        assert settings == expected_settings

        with loc.open('r') as fb:
            assert fb.read() == INITIAL_DEFAULT_CONFIG


class TestPrepare:

    def test(self, monkeypatch):
        settings_marker = object()
        discover_settings = pretend.call_recorder(lambda: settings_marker)
        monkeypatch.setattr('nebu.config.discover_settings',
                            discover_settings)

        env = prepare()

        assert callable(env['closer'])
        assert env['settings'] is settings_marker
