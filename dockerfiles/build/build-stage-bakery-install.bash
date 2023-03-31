#!/bin/bash
set -e

# shellcheck disable=SC1090
source $PROJECT_ROOT/venv/bin/activate

pip3 install $BAKERY_SRC_ROOT/scripts/.
npm --prefix $BAKERY_SRC_ROOT/scripts install --production $BAKERY_SRC_ROOT/scripts
