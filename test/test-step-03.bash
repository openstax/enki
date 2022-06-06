#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

BOOK_DIR=../data/test-book

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov03 \
../enki --keep-data --data-dir $BOOK_DIR --command all-git-web --repo 'philschatz/tiny-book' --book-slug 'book-slug1' --style chemistry --ref main --start-at git-disassemble


# Verify we can build a commit that is not on the main branch
SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov03 \
../enki --keep-data --data-dir $BOOK_DIR --command all-git-web --repo 'philschatz/tiny-book' --book-slug 'book-slug1' --style chemistry --ref @458dfb710e9af3d00d6f7e0be45fc819b955d931 --start-at git-disassemble


# Check local-preview works
SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov03 \
../enki --keep-data --data-dir $BOOK_DIR --command local-preview

# Check local-preview directories / files existing
[ -d "$BOOK_DIR/local-preview" ] || echo "Directory $BOOK_DIR/local-preview missing"
[ -d "$BOOK_DIR/local-preview/contents" ] || echo "Directory $BOOK_DIR/local-preview/contents missing"
[ -d "$BOOK_DIR/local-preview/contents" ] || echo "Directory $BOOK_DIR/local-preview/contents missing"
[[ -L "$BOOK_DIR/local-preview/resources" && -d "$BOOK_DIR/local-preview/resources" ]] || echo "Symlink and/or directory $BOOK_DIR/local-preview/resources missing"
