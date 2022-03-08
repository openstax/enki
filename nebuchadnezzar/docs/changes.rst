==========
Change Log
==========

9.15.0

- Ensure all IDs are unique and remove randomly-generated IDs

9.14.0

- fix the pattern used to match embedded exercises

9.13.1

- fix license text so it is not hardcoded

9.13.0

- add data-type to code elements

9.12.0

- Include Error context when exercise has more than one link

9.11.0
-----

- Add support for double-underline

9.10.0
-----

- Add cases for selecting injected exercise links

9.7.0
-----

- Update the injected exercise HTML format

9.6.0
-----

- Neb assemble will now mutlithread exercise fetching (#172)

9.5.1
-----

- Allow a limit to be specified to the number of concurrent requests made (default 8) (#173)
- Setting limit to 1 should yield synchronous-like behavior

9.5.0
-----

- Use asyncio/aiohttp to speed up requests and improve performance of neb get (#166)

9.4.0
-----

- Support exercise using nickname #exercise/XXXXX (#162)
- Remove upload pypi step in Jenkinsfile (#163)

9.3.0
-----

- Fetch exercises during ``neb assemble`` (#160)

9.2.1
-----

- Use PyPi distribution for neb-tasks (#161)

9.2.0
-----

- Add twine check on travis (#155)
- Change Connexions to OpenStax in setup.py
- Add neb-tasks as an optional dependency from git repo
- Add command help sections and relevant tests
- Add "ping" command to check credentials and permissions (#158)

9.1.0
-----

- Fix assemble when collection.xml doesn't use all modules (#150)
- Remove mathify from nebuchadnezzar (#154)
- Add Dockerfile for nebuchadnezzar (#153)
- Improve message when file exists on assemble (#152)
- Only publish feature: disregard non-utf8 chars decoding (#148)

9.0.2
--------------

- UTF-8 Encoding and Module versioning #273 - Disregard decoded chars when detecting what's changed (PR #148)

9.1.0b6
-------

- Remove cascading call of ``assemble`` in ``mathify`` (#149)

9.1.0b5
-------

- Fix internal reference links within the output of ``assemble`` (#147)

9.1.0b4
-------

- Revert defaulting to using the non-collated version (#146)

9.1.0b3
-------

- Fix to add retries to ``get`` by using a requests session (#142)
- Fix to write content to disk as bytes during ``get`` (#144)
- Change to always default to fetching the non-collated version (#143)
- Change that will not require the output dir to not existing during
  ``assemble`` (#145)

9.1.0b2
-------

- Fix to require cnxml >=3.0.1 for metadata parsing support
- Remove the ``cnxml-to-html`` command from neb, as it has been superseded
  by the functionality in the ``assemble`` command (#140)
- Fix to transform the summary text during assembly (#141)

9.1.0b1
-------

- Add ``cnxml-to-html`` command to transform index.cnxml to html.
- Add models for producing cnx-epub objects from litezip structured
  data (#134)
- Add the ``assemble`` command for assembling litezip structured data into
  a single-page-html file. (#136)
- Add the ``mathify`` command to convert MathML to SVG or HTML+CSS using
  MathJax. (#130)

9.0.1
-----

- Do not fetch auto-generated HTML file

9.0.0
-----

- Add switch to fetch all associated resources (images).
- Allow specifying minor version for `get`, with three-part version `1.X.Y`.

8.0.5
-----

- Update cnx-litezip for >= 1.6.0

8.0.4
-----

- Fix spacing when generating sha1sum files on `get`.

8.0.3
-----

- Fix pipeline stage for releasing the python package.

8.0.2
-----

- Fix http verb to check credentials before publish.

8.0.1
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
