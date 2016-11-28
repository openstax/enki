CNX Nebu Publishing Utility
===========================

This is a command-line interface for interacting with connexions content. The tools is primarily used to publish content to the cnx.org website.

This software requires:

- Python >= 3.5
- JRE >= 6

Install
=======

1. Install `git`
1. Install `python3` (on OSX you can run `brew install python3`)
1. Install `virtualenv`
1. Download the source `git clone https://github.com/Connexions/nebuchadnezzar`
1. `cd /path/to/nebuchadnezzar`
1. Initialize the python virtual environment:
  1. `virtualenv ./venv/ --python=python3.5`
  1. `source ./venv/bin/activate`
  1. `python setup.py develop`

Run
===

1. Open up a new terminal
1. `cd /path/to/nebuchadnezzar/`
1. `source ./venv/bin/activate`
1. Now you can run various commands:
  - `neb --help` for help with the various commands

License
-------

This software is subject to the provisions of the GNU Affero General
Public License Version 3.0 (AGPL). See [license.txt](./license.txt) for details.
Copyright (c) 2016 Rice University
