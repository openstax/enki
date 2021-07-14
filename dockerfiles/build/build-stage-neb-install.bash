#!/bin/bash
set -e

cd $PROJECT_ROOT/nebuchadnezzar/

source $PROJECT_ROOT/venv/bin/activate \
    && pip3 install .
