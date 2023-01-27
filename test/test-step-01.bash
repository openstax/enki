#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

BOOK_DIR=../data/test-book
BUSI_DIR=../data/test-busi
COVERAGE_DIR=../coverage

[[ -d $BOOK_DIR ]] && rm -rf $BOOK_DIR
[[ -d $BUSI_DIR ]] && rm -rf $BUSI_DIR

../enki --help
