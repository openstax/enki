#!/bin/bash
set -e

BOOK_DIR=./data/test-book
SOCI_DIR=./data/test-soci
KCOV_COLLECTOR=./data/kcov-collector
COVERAGE_DIR=./coverage

[[ -d $BOOK_DIR ]] && rm -rf $BOOK_DIR
[[ -d $SOCI_DIR ]] && rm -rf $SOCI_DIR
[[ -d $KCOV_COLLECTOR ]] && rm -rf $KCOV_COLLECTOR
[[ -d $COVERAGE_DIR ]] && rm -rf $COVERAGE_DIR

mkdir -p $KCOV_COLLECTOR
