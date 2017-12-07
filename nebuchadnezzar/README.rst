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

See https://github.com/Connexions/cnxml#editvalidate-files-using-atomio for details.

License
-------

This software is subject to the provisions of the GNU Affero General
Public License Version 3.0 (AGPL). See `<LICENSE.txt>`_ for details.
Copyright (c) 2016 Rice University
