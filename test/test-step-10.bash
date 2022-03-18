#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

DATA_ROOT=../data
COVERAGE_DIR=../coverage
[[ -d $COVERAGE_DIR ]] || mkdir $COVERAGE_DIR
pip install "../output-producer-service/bakery/src/scripts/.[test]"
flake8 "../output-producer-service/bakery/src/scripts" --max-line-length=100
pytest --cov=bakery_scripts --cov-append --cov-report=html:$COVERAGE_DIR ../output-producer-service/ -vvv
ls -alt $COVERAGE_DIR