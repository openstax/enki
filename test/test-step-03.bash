#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

BOOK_DIR=../data/test-book

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov03 \
START_AT_STEP=git-disassemble \
../enki $BOOK_DIR all-git-web 'philschatz/tiny-book/book-slug1' chemistry main


# Verify we can build a commit that is not on the main branch
SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov03 \
START_AT_STEP=git-disassemble \
../enki $BOOK_DIR all-git-web 'philschatz/tiny-book/book-slug1' chemistry @458dfb710e9af3d00d6f7e0be45fc819b955d931