CNX Nebu Publishing Utility
===========================

This is a command-line interface for interacting with connexions content. The tools is primarily used to publish content to the cnx.org website.

This software requires:

- Python >= 3.5
- JRE >= 6


Install
=======

1. Install ``python3`` (on OSX you can run ``brew install python3``)
#. Run ``pip3 install --upgrade pip setuptools`` in a terminal to upgrade python tools
#. Run ``pip3 install nebuchadnezzar`` in a terminal
#. Run ``neb --help`` to verify the application is installed


Development
===========

Install
-------

1. Install ``python3`` (on OSX you can run ``brew install python3``)
#. Initialize the python virtual environment:

   a. ``virtualenv ./venv/ --python=python3.5``
   #. ``source ./venv/bin/activate``
   #. ``pip3 install --upgrade pip setuptools``
   #. ``python setup.py develop``

Developer Run
-------------

1. Open up a new terminal
#. ``source ./venv/bin/activate``
#. Now you can run various commands:

   - ``neb --help`` for help with the various commands

Configuring an Editor
=====================
Preparation
-----------

#. Install https://atom.io

Install (with automatic Atom config)
------------------------------------

#. Start up Atom
#. Install the ``linter-autocomplete-jing`` package

#. Type <kbd>⌘</kbd>+<kbd>,</kbd> (for Mac) to open Settings (or click **Atom**, **Preferences...** in the menu bar)

   #. Click **Install** in the left-hand-side
   #. Enter ``linter-autocomplete-jing`` and click **Install**
   #. **Alternative:** run ``apm install linter-autocomplete-jing`` from the commandline

#. Run ``neb atom-config`` (**NOTE:** *This will overwrite your Atom config file. If you'd prefer updating the config file yourself, see `Manual Atom config`_ below.*)
#. Restart Atom
#. Open an unzipped complete-zip. (I run ``atom ~/Downloads/col1234_complete`` **From a terminal**)
#. Verify by opening an ``index.cnxml`` file and typing in ``<figure>`` somewhere in the file. If it is a valid location then it should auto-add ``id=""`` for you

Manual Atom config
------------------

Add the following to your Atom configuration by clicking **Atom**, **Config** in the menu bar and copying and pasting the below (**NOTE**: indentation is important)::

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
Public License Version 3.0 (AGPL). See `<LICENSE.txt>`_ for details.
Copyright (c) 2016-2018 Rice University
