#!/bin/bash
set -e
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"
[[ ${TRACE_ON} ]] && set -x

BOOK_DIR=../data/test-book

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov03 \
START_AT_STEP=git-disassemble \
../cli.sh $BOOK_DIR all-git-web 'philschatz/tiny-book/book-slug1' chemistry main
