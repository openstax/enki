#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

BOOK_DIR=../data/test-book

# Run the first step just to make sure the codepath works
KCOV_DIR=_kcov02-a \
../enki --clear-data --data-dir $BOOK_DIR --command local-create-book-directory --repo 'philschatz/tiny-book' --book-slug 'book-slug1' --ref main

# Build git PDF and web
SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov02-b \
../enki --keep-data --data-dir $BOOK_DIR --command all-pdf --repo tiny-book --ref main # without slug

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov02-c \
../enki --keep-data --data-dir $BOOK_DIR --command all-pdf --repo 'philschatz/tiny-book' --book-slug 'book-slug1' --ref main # with slug

# ################################
# HACK: Add math to the cnxml to 
# simulate exercise injection
# (this is technically invalid cnxml)
# ################################

while read -r module_file; do
    # Why not sed --in-place=.orig ? Because sed is different on MacOS
    awk '{
        if ($0 ~ /<\/content>/) {
            print "<!-- HACK: injected math -->"
            print "<div id=\"math-element\" data-math=\"\\frac{2}{5}\"></div>"
        }
        print
    }' "$module_file" > "$module_file.math"
    mv "$module_file" "$module_file.orig"
    mv "$module_file.math" "$module_file"
done < <(find $BOOK_DIR -name "index.cnxml")

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov02-d \
../enki --keep-data --data-dir $BOOK_DIR --command all-pdf --start-at step-prebake --repo tiny-book --book-slug book-slug1 --ref main

find $BOOK_DIR -name "index.cnxml.orig" -exec bash -cxe 'mv $0 $(dirname $0)/index.cnxml' {} \;

# ################################
# Clone a branch, 
# build the PDF URL,
# and verify it is URL-encoded
# ################################

SKIP_DOCKER_BUILD=1 \
../enki --keep-data --data-dir $BOOK_DIR --command all-pdf --repo 'philschatz/tiny-book' --book-slug 'book-slug1' --ref long-lived-branch-for-testing-with-#-char

SKIP_DOCKER_BUILD=1 \
../enki --keep-data --data-dir $BOOK_DIR --command step-pdf-meta

expected_pdf_filename='book-slug1-long-lived-branch-for-testing-with-%23-char-git--123456.pdf'
actual_pdf_url=$(cat $BOOK_DIR/_attic/IO_ARTIFACTS/pdf_url)
actual_pdf_filename=$(basename "$actual_pdf_url")
[[ $expected_pdf_filename == $actual_pdf_filename ]] || {
    echo "PDF URL was not escaped. Expected '$expected_pdf_filename' but got '$actual_pdf_filename'"
}
