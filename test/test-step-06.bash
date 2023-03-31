#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

BOOK_DIR=../data/test-book

xhtml_files_dir="$BOOK_DIR/_attic/IO_DOCX/content"
# shellcheck disable=SC2206
files=($xhtml_files_dir/*.xhtml)
keep_file="${files[0]}"

mv "$keep_file" "$keep_file.keep"

echo "Note: Removing all xhtml files except one to speed up this test step: $keep_file"
# find "$xhtml_files_dir" ! -name "$keep_file" -name '*.xhtml' -type f -exec rm -f {} +
rm -rf $xhtml_files_dir/*.xhtml
mv "$keep_file.keep" "$keep_file"

# kcov causes this step to hang so skip the KCOV_DIR (probably the pm2 mathml2svg background process)
SKIP_DOCKER_BUILD=1 \
../enki --keep-data --data-dir $BOOK_DIR --command all-git-gdoc --start-at step-docx