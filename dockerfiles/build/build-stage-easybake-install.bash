#!/bin/bash
set -e

# shellcheck disable=SC1090
source $VENV_ROOT/bin/activate

python3 -m pip install $PROJECT_ROOT/cnx-easybake/