#!/bin/bash
set -e

cd $PROJECT_ROOT/nebuchadnezzar/

source $PROJECT_ROOT/venv/bin/activate \
    && pip3 install -U setuptools wheel \
    && pip3 install -r ./requirements/main.txt
