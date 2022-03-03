#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

BOOK_DIR=../data/test-book

# Run the first step just to make sure the codepath works
KCOV_DIR=_kcov02-a \
../enki --data-dir $BOOK_DIR --command local-create-book-directory --repo 'philschatz/tiny-book' --book-slug 'book-slug1' --style default --ref main

# Build git PDF and web
SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov02-b \
../enki --data-dir $BOOK_DIR --command all-git-pdf --repo 'philschatz/tiny-book' --book-slug 'book-slug1' --style default --ref main

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov02-c \
../enki --data-dir $BOOK_DIR --command git-validate-cnxml


# ################################
# Clone a branch, 
# build the PDF URL,
# and verify it is URL-encoded
# ################################

SKIP_DOCKER_BUILD=1 \
../enki --data-dir $BOOK_DIR --command all-git-pdf --repo 'philschatz/tiny-book' --book-slug 'book-slug1' --style default --ref long-lived-branch-for-testing-with-#-char

SKIP_DOCKER_BUILD=1 \
../enki --data-dir $BOOK_DIR --command git-pdfify-meta

expected_pdf_filename='book-slug1-long-lived-branch-for-testing-with-%23-char-git--123456.pdf'
actual_pdf_url=$(cat $BOOK_DIR/_attic/IO_ARTIFACTS/pdf_url)
actual_pdf_filename=$(basename "$actual_pdf_url")
[[ $expected_pdf_filename == $actual_pdf_filename ]] || {
    echo "PDF URL was not escaped. Expected '$expected_pdf_filename' but got '$actual_pdf_filename'"
}
