#!/bin/bash
set -e

# shellcheck disable=SC1090
source $PROJECT_ROOT/venv/bin/activate

python3 -m pip install $PROJECT_ROOT/cnx-easybake/