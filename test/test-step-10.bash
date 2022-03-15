#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

DATA_ROOT=../data
COVERAGE_DIR=../coverage
pip install "../output-producer-service/bakery/src/scripts/.[test]"
pytest "../output-producer-service/bakery"