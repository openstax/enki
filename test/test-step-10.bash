#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

DATA_ROOT=../data
COVERAGE_DIR=../coverage
pwd
ls -alt
pip install ../output-producer-service/bakery/scr/scripts/.[test]
pytest bakery