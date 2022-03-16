#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

DATA_ROOT=../data
COVERAGE_DIR=../coverage
pip install "../output-producer-service/bakery/src/scripts/.[test]"
flake8 "../output-producer-service/bakery/src/scripts/*.py" --max-line-length=100
pytest --cov=bakery_scripts --cov-report=html --cov-report=term "../output-producer-service/bakery" -vvv --junitxml=/tmp/test-reports/junit.xml