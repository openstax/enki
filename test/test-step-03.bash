#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

BOOK_DIR=../data/test-book

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov03 \
../enki --data-dir $BOOK_DIR --command all-git-web --repo 'philschatz/tiny-book' --book-slug 'book-slug1' --style chemistry --ref main --start-at git-disassemble


# Verify we can build a commit that is not on the main branch
SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov03 \
../enki --data-dir $BOOK_DIR --command all-git-web --repo 'philschatz/tiny-book' --book-slug 'book-slug1' --style chemistry --ref @458dfb710e9af3d00d6f7e0be45fc819b955d931 --start-at git-disassemble