#!/bin/bash
set -e

# shellcheck disable=SC1090
source $PROJECT_ROOT/venv/bin/activate

pip3 install -r $BAKERY_SRC_ROOT/scripts/requirements.txt


pip install coverage==5.5 # Because we need to instrument 3rd-party packages: https://nedbatchelder.com/blog/202104/coveragepy_and_thirdparty_code.html
