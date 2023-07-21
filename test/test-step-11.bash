#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"

BUSI_DIR=../data/test-busi

SKIP_DOCKER_BUILD=${SKIP_DOCKER_BUILD:-1} \
KCOV_DIR=_kcov11-a \
../enki --clear-data --data-dir $BUSI_DIR --command all-epub --repo 'openstax/osbooks-business-law' --book-slug business-law-i-essentials --ref main

SKIP_DOCKER_BUILD=${SKIP_DOCKER_BUILD:-1} \
STUB_AWS_CLI=1 \
KCOV_DIR=_kcov11-b \
../enki --keep-data --data-dir $BUSI_DIR --command step-upload-epub

BOOK_DIR=$BUSI_DIR
expected_repo="openstax-osbooks-business-law"
expected_version="main"
expected_job_id="-123456"
expected_book_slug='business-law-i-essentials'
expected_extension="epub"
expected_mime_type="application/epub+zip"
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
actual_contents="$(cat $BOOK_DIR/_attic/IO_ARTIFACTS/aws_args)"
if [[ "$actual_contents" != "$expected_contents" ]]; then
    echo "Bad AWS CLI args."
    echo "Expected value: $expected_contents"
    echo "Actual value:   $actual_contents"
    exit 1
fi
