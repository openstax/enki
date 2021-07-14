#!/bin/bash
set -e

cd $PROJECT_ROOT/cnx-easybake/
source $PROJECT_ROOT/venv/bin/activate && python3 -m pip install -r requirements/main.txt
