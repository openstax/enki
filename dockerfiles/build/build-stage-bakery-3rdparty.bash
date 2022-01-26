#!/bin/bash
set -e

# shellcheck disable=SC1090
source $VENV_ROOT/bin/activate

pip3 install -r $BAKERY_SRC_ROOT/scripts/requirements.txt
