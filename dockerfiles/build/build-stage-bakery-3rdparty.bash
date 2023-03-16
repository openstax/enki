#!/bin/bash
set -e

# shellcheck disable=SC1090
source $PROJECT_ROOT/venv/bin/activate

npm --prefix $BAKERY_SRC_ROOT/scripts install --production $BAKERY_SRC_ROOT/scripts
pip3 install -r $BAKERY_SRC_ROOT/scripts/requirements.txt
