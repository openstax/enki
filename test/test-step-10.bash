#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

DATA_ROOT=../data
COVERAGE_DIR=../coverage
pip install --upgrade "../output-producer-service/bakery/src/scripts/.[test]"
flake8 "../output-producer-service/bakery/src/scripts" --max-line-length=100
pytest --cov --cov-append ../output-producer-service/ -vvv