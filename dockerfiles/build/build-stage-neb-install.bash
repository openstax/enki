#!/bin/bash
set -e

# shellcheck disable=SC1090
source $PROJECT_ROOT/venv/bin/activate

pip3 install $PROJECT_ROOT/nebuchadnezzar/
