#!/bin/bash
set -e

cd $BAKERY_SRC_ROOT
source $PROJECT_ROOT/venv/bin/activate && pip3 install -r scripts/requirements.txt
