CNX Nebu Publishing Utility
===========================

This is a command-line interface for interacting with connexions content. The tools is primarily used to publish content to the cnx.org website.

This software requires:

- Python >= 3.5
- JRE >= 6


Install
=======

1. Install `python3` (on OSX you can run `brew install python3`)
#. Run `pip3 install --upgrade pip setuptools` in a terminal to upgrade python tools
#. Run `pip3 install nebuchadnezzar` in a terminal
#. Run `neb --help` to verify the application is installed


Development
===========

Install
-------

1. Install `python3` (on OSX you can run `brew install python3`)
#. Initialize the python virtual environment:

   a. `virtualenv ./venv/ --python=python3.5`
   #. `source ./venv/bin/activate`
   #. `pip3 install --upgrade pip setuptools`
   #. `python setup.py develop`

Developer Run
-------------

1. Open up a new terminal
#. `source ./venv/bin/activate`
#. Now you can run various commands:

   - `neb --help` for help with the various commands

Configuring an Editor
=====================
Preparation
^^^^^^^^^^^

#. Install https://atom.io
#. Get the cnxml RNG Schema files

   #. Download the most recent version from https://github.com/Connexions/cnxml/releases (click the "zip" link)

      - It should be in your Download foler
      - Move it to ~/.neb/

   #. Unzip the file
   #. It should have created a folder named something like `cnxml-2.0.0` (with `/cnxml/xml/cnxml/schema/rng/0.7/cnxml-jing.rng` in it)
   #. Rename the folder to be something you are unlikely to accidentally delete (like `cnxml-validation`)

      - Remember the name for later when you are editing `~/.atom/config.cson`

Install
^^^^^^^

#. Start up Atom
#. Install the `linter-autocomplete-jing` package

#. Type <kbd>⌘</kbd>+<kbd>,</kbd> (for Mac) to open Settings (or click **Atom**, **Preferences...** in the menu bar)

   #. Click **Install** in the left-hand-side
   #. Enter `linter-autocomplete-jing` and click **Install**
   #. **Alternative:** run `apm install linter-autocomplete-jing` from the commandline

#. Edit `~/.atom/config.cson` by clicking **Atom**, **Config** in the menu bar and add the following lines (at the bottom of this document)
#. Restart Atom
#. Open an unzipped complete-zip. (I run `atom ~/Downloads/col1234_complete` **From a terminal**)
#. Verify by opening an `index.cnxml` file and typing in `<figure>` somewhere in the file. If it is a valid location then it should auto-add `id=""` for you


Changes to `~/.atom/config.cson`::

    "*":
      core:
        customFileTypes:
    
          # Add this to the bottom of the customFileTypes area.
          # Note: Indentation is important!
          "text.xml": [
            "index.cnxml"
          ]
    
    
      # And then this to the bottom of the file
      # 1. Make sure "linter-autocomplete-jing" only occurs once in this file!
      # 1. make sure it is indented by 2 spaces just like it is in this example.
    
      "linter-autocomplete-jing":
        displaySchemaWarnings: true
        rules: [
          {
            priority: 1
            test:
              pathRegex: ".cnxml$"
            outcome:
              schemaProps: [
                {
                  lang: "rng"
                  path: "~/.neb/cnxml-validation/cnxml/xml/cnxml/schema/rng/0.7/cnxml-jing.rng"
                }
              ]
          }
        ]

License
-------

This software is subject to the provisions of the GNU Affero General
Public License Version 3.0 (AGPL). See license.txt for details.
Copyright (c) 2016 Rice University

See https://github.com/Connexions/cnxml#editvalidate-files-using-atomio for details.

License
-------

This software is subject to the provisions of the GNU Affero General
Public License Version 3.0 (AGPL). See `<LICENSE.txt>`_ for details.
Copyright (c) 2016 Rice University
