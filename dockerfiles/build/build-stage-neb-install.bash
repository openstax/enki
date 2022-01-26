#!/bin/bash
set -e

# shellcheck disable=SC1090
source $VENV_ROOT/bin/activate

pip3 install $PROJECT_ROOT/nebuchadnezzar/
