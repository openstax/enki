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

local_preview_data_missing_halt () {
    echo "local-preview: $1"
    exit 1
}

LOCAL_PREVIEW="$BOOK_DIR/local-preview"
[ -d "$LOCAL_PREVIEW" ] || local_preview_data_missing_halt "Directory $LOCAL_PREVIEW missing"
[ -d "$LOCAL_PREVIEW/contents" ] || local_preview_data_missing_halt "Directory $LOCAL_PREVIEW/contents missing"
[[ -L "$LOCAL_PREVIEW/resources" && -d "$LOCAL_PREVIEW/resources" ]] || local_preview_data_missing_halt "Symlink and/or directory $LOCAL_PREVIEW/resources missing"
[ -e "$LOCAL_PREVIEW/resources/4e88fcaf0d07298343a7cb933926c4c0c6b5b017" ] || local_preview_data_missing_halt "Duck wearing hat photo missing"
CONTENT_SAMPLE_FILE="$LOCAL_PREVIEW/contents/00000000-0000-0000-0000-000000000000@458dfb7:11111111-1111-1111-1111-111111111111.xhtml"
[ -e "$CONTENT_SAMPLE_FILE" ] || local_preview_data_missing_halt "$CONTENT_SAMPLE_FILE content file missing"
grep -q "\<img src=\"..\/resources\/4e88fcaf0d07298343a7cb933926c4c0c6b5b017\"" "$CONTENT_SAMPLE_FILE" || local_preview_data_missing_halt "image content not found in content file"