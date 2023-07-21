#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

BOOK_DIR=../data/test-book

# Test from the start with book slug
SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov05-a \
../enki --keep-data --data-dir $BOOK_DIR --command all-docx --repo 'philschatz/tiny-book' --book-slug 'book-slug1' --ref main

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov05-b \
STUB_UPLOAD=1 \
../enki --keep-data --data-dir $BOOK_DIR --command step-upload-docx

expected_repo="philschatz-tiny-book"
expected_version="main"
expected_job_id="-123456"
expected_book_slug="book-slug1"
expected_extension="zip"
expected_mime_type="application/zip"
expected_filename="$expected_repo-$expected_version-$expected_job_id-$expected_book_slug.$expected_extension"
expected_contents='[{"url":"https://openstax-sandbox-cops-artifacts.s3.amazonaws.com/'"$expected_filename"'","slug":"'"$expected_book_slug"'"}]'
actual_contents="$(cat $BOOK_DIR/_attic/IO_ARTIFACTS/pdf_url)"
if [[ "$actual_contents" != "$expected_contents" ]]; then
    echo "Bad artifact urls."
    echo "Expected value: $expected_contents"
    echo "Actual value:   $actual_contents"
    exit 1
fi

expected_contents="s3 cp /data/artifacts-single/$expected_book_slug.$expected_extension s3://openstax-sandbox-cops-artifacts/$expected_filename --acl public-read --content-type $expected_mime_type"
actual_contents="$(cat $BOOK_DIR/_attic/IO_ARTIFACTS/aws_args_1)"
if [[ "$actual_contents" != "$expected_contents" ]]; then
    echo "Bad AWS CLI args."
    echo "Expected value: $expected_contents"
    echo "Actual value:   $actual_contents"
    exit 1
fi


# Test without book slug
rm $BOOK_DIR/_attic/IO_BOOK/slugs
SKIP_DOCKER_BUILD=1 \
../enki --data-dir $BOOK_DIR --command all-docx --start-at step-disassemble --repo 'philschatz/tiny-book' --ref main

SKIP_DOCKER_BUILD=1 \
STUB_UPLOAD=1 \
../enki --keep-data --data-dir $BOOK_DIR --command step-upload-docx


