#!/bin/bash
set -e
[[ ${TRACE_ON} ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

BOOK_DIR=../data/test-book
SOCI_DIR=../data/test-soci
COVERAGE_DIR=../coverage

[[ -d $BOOK_DIR ]] && rm -rf $BOOK_DIR
[[ -d $SOCI_DIR ]] && rm -rf $SOCI_DIR

KCOV_DIR=_kcov01 ../cli.sh $BOOK_DIR --help > /dev/null
