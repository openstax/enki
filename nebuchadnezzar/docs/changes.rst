==========
Change Log
==========

?X.Y.Z
-----

- Add `list` command, to list individual environments defined in configuration.

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
