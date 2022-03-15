#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

DATA_ROOT=../data
COVERAGE_DIR=../coverage
pip install "../output-producer-service/bakery/src/scripts/.[test]"
pytest --cov=bakery_scripts --cov-report=html --cov-report=term --junitxml=/tmp/test-reports/junit.xml "../output-producer-service/bakery"