#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

BOOK_DIR=../data/test-book

# Build git PDF and web
SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov02-a \
CODE_VERSION=main \
../cli.sh $BOOK_DIR all-git-pdf 'philschatz/tiny-book/book-slug1' chemistry main

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov02-b \
../cli.sh $BOOK_DIR git-validate-cnxml