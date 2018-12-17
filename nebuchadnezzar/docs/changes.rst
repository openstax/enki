==========
Change Log
==========

7.2.1
-----

- Add staged.cnx.org environments to the default configuration file.

7.2.0
-----

- Only publish content that has changed.

7.1.2
-----

- Preemptively check for credentials
- Allow outside of CWD `get` output dir.

7.1.1
-----

- Correct numbering for 'Introduction' pages.

7.1.0
-----

- Support book tree for both `get` and `publish`

7.0.1
-----

- fix litezip 1.5 compatability

7.0.0
-----

- Publish resources!

6.1.0
-----

- Append version number to checkout folder - col1234_1.X.Y

6.0.1
-----

- fixup basic auth header - use library rather than roll our own

6.0.0
-----

- Add Basic Auth authentication to publish

5.1.0
-----

- Update cnxml for >=2.2.0 (#74)

- allow non-descendent path to xml in error output

- update expected test output for new jing

5.0.3
-----

- Update tests to match new error messages from cnxml v2.2.0

5.0.2
-----

- Add content*.cnx.org environments to the default configuration file.

5.0.1
-----

- Fix ``FileNotFoundError`` raised on on user's first run of Nebuchadnezzar.
  This was caused by the parent directory not existing, so the default
  behavior of writing the default config failed with this error.
  See https://github.com/Connexions/nebuchadnezzar/issues/66

5.0.0
-----

- Split the cli module into submodules, one for each subcommmand.

- Add a skip-validation option flag to the publish command.

- Suggest a newer version of Neb to install on ``--version`` when
  it is determined that the user's version is older than the last
  release.
  See https://github.com/Connexions/nebuchadnezzar/issues/16

- Resource/image files will no longer be copied into the working
  directory when using ``neb get``.
  See https://github.com/Connexions/nebuchadnezzar/issues/61

4.0.0
-----

- Retrieve content from archive, rather than legacy.

- Make the collectiom version required for
  ``neb get [env] [colid] [col_version]``.
  See https://github.com/Connexions/nebuchadnezzar/issues/54

- Warn and prompt if requested not most recently published version.

- Move all subcommand common options to the subcommands.
  ``neb [OPTIONS] get [OPTIONS] ...`` becomes ``neb get [OPTIONS``.
  For example, ``neb -v get ...`` becomes ``neb get -v ...``.
  See https://github.com/Connexions/nebuchadnezzar/issues/48

3.1.0
-----

- Fix the 'get' command to request a specific version of the completezip,
  rather than rely on the 'latest' specifier, which has the issue of
  requesting a cached completezip.
  See https://github.com/Connexions/nebuchadnezzar/issues/44

3.0.1
-----

- Fix 'get' issue where the content exists but the completezip is not
  available for download.
  See https://github.com/Connexions/nebuchadnezzar/issues/28

3.0.0
-----

- Adjusted the publication api point in response to the api change in Press.

2.1.0
-----

- Add ``list`` command, to list individual environments defined
  in configuration.

2.0.1
-----

- Clarify the error message produced when attempting to get content
  that is already downloaded. This clarification is for when ``neb get``
  would colide with an existing directory of the same name.

2.0.0
-----

- Add the ability to define individual environments via a configuration file.

1.4.2
-----

- Update the README with instructions that use the 'atom-config' command.

1.4.1
-----

- Fix atom config filepath to RNG file.
  See https://github.com/Connexions/nebuchadnezzar/issues/18.

1.4.0
-----

- Modify 'config-atom' command to make a backup of the existing config.

1.3.0
-----

- Add a '--version' option to show the currently installed version.

1.2.0
-----

- Add a 'config-atom' command to configure the atom text editor.

1.1.2
-----

- Fix to allow the 'get' command to use the temporary environment
  variables to modify the url for acquiring the content.

1.1.1
-----

- Fix publishing url to allow the user to modify the url scheme.

1.1.0
-----

- Adds a publish command that communicates with a Press service.
