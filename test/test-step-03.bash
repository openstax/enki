#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

BOOK_DIR=../data/test-book

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov03 \
START_AT_STEP=git-disassemble \
CODE_VERSION=main \
../cli.sh $BOOK_DIR all-git-web 'philschatz/tiny-book/book-slug1' chemistry main
