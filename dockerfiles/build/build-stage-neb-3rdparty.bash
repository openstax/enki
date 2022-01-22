#!/bin/bash
set -e

# shellcheck disable=SC1090
source $VENV_ROOT/bin/activate

pip3 install -U setuptools wheel
pip3 install -r $PROJECT_ROOT/nebuchadnezzar/requirements/main.txt
