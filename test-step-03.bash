#!/bin/bash
set -e

BOOK_DIR=./data/test-book

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov03 \
START_AT_STEP=git-disassemble \
./cli.sh $BOOK_DIR all-git-web 'philschatz/tiny-book/book-slug1' chemistry main
