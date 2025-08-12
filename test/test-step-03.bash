#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"


BOOK_DIR=../data/test-book
ARTIFACTS_URL_PATH="$BOOK_DIR/_attic/IO_ARTIFACTS/artifact_urls.json"

rm -f $BOOK_DIR/_attic/IO_ARTIFACTS/upload_ancillaries_args_*

# Test from the start with book slug
SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov03-a \
../enki --keep-data --data-dir $BOOK_DIR --command all-web --repo 'philschatz/tiny-book' --book-slug 'book-slug1' --ref '03e68a5f78e8fb2ceab04aa719a6daf30a7999b0'

SKIP_DOCKER_BUILD=1 \
STUB_UPLOAD="corgi" \
KCOV_DIR=_kcov03-b \
../enki --keep-data --data-dir $BOOK_DIR --command step-upload-book --repo 'philschatz/tiny-book' --book-slug 'book-slug1' --ref '03e68a5f78e8fb2ceab04aa719a6daf30a7999b0'

if [[ $(find $BOOK_DIR/_attic/IO_ARTIFACTS -type f -name 'upload_ancillaries_args_*' | wc -l) -gt 0 ]]; then
    echo "Should not upload ancillaries for CORGI builds"
    exit 1
fi

# Check that upload was called with expected values
counter=0
while IFS=$'\n' read -r expected_contents; do
    counter=$((counter+1))
    actual_contents="$(cat $BOOK_DIR/_attic/IO_ARTIFACTS/aws_args_$counter)"
    if [[ "$expected_contents" != "$actual_contents" ]]; then
        echo "Bad AWS CLI args."
        echo "Expected value: $expected_contents"
        echo "Actual value:   $actual_contents"
        exit 1
    fi
done <<EOF
s3 cp --recursive /tmp/build/0000000/artifacts-single s3://openstax-sandbox-cops-artifacts/apps/archive-localdev/test/contents
s3 cp --recursive /tmp/build/0000000/resources/03e68a5/ s3://openstax-sandbox-cops-artifacts/apps/archive-localdev/test/resources/03e68a5
s3 cp --recursive /tmp/build/0000000/resources/styles/ s3://openstax-sandbox-cops-artifacts/apps/archive-localdev/test/resources/styles
s3 cp /tmp/build/0000000/jsonified-single/book-slug1.toc.json s3://openstax-sandbox-cops-artifacts/apps/archive-localdev/test/contents/00000000-0000-0000-0000-000000000000@03e68a5.json
s3 cp /tmp/build/0000000/jsonified-single/book-slug1.toc.xhtml s3://openstax-sandbox-cops-artifacts/apps/archive-localdev/test/contents/00000000-0000-0000-0000-000000000000@03e68a5.xhtml
EOF
# If you ever need to update the above list, just do `cat ../data/test-book/_attic/IO_ARTIFACTS/aws_args_*` and copy/paste :)


counter=0
while IFS=$'\n' read -r expected_contents; do
    counter=$((counter+1))
    actual_contents="$(cat $BOOK_DIR/_attic/IO_ARTIFACTS/copy_resources_s3_args_$counter)"
    if [[ "$expected_contents" != "$actual_contents" ]]; then
        echo "copy-resource-s3 args."
        echo "Expected value: $expected_contents"
        echo "Actual value:   $actual_contents"
        exit 1
    fi
done <<EOF
/tmp/build/0000000/resources openstax-sandbox-cops-artifacts apps/archive-localdev/test/resources
EOF
# If you ever need to update the above list, just do `cat ../data/test-book/_attic/IO_ARTIFACTS/copy_resources_s3_args_*` and copy/paste :)


expected_book_slug="book-slug1"
expected_ref=03e68a5
expected_url="https://rex-test/apps/rex/books/00000000-0000-0000-0000-000000000000@$expected_ref/pages/subcollection?archive=https://test-cloudfront-url/apps/archive-localdev/test"
expected_contents='[{"url":"'"$expected_url"'","slug":"'"$expected_book_slug"'"}]'
actual_contents="$(cat $ARTIFACTS_URL_PATH)"
if [[ "$actual_contents" != "$expected_contents" ]]; then
    echo "Bad artifact urls."
    echo "Expected value: $expected_contents"
    echo "Actual value:   $actual_contents"
    exit 1
fi

# Test without book slug
rm $BOOK_DIR/_attic/IO_BOOK/slugs
SKIP_DOCKER_BUILD=1 \
../enki --data-dir $BOOK_DIR --command all-web --start-at step-disassemble --repo 'philschatz/tiny-book' --ref '03e68a5f78e8fb2ceab04aa719a6daf30a7999b0'

SKIP_DOCKER_BUILD=1 \
STUB_UPLOAD="corgi" \
../enki --keep-data --data-dir $BOOK_DIR --command step-upload-book --repo 'philschatz/tiny-book' --ref '03e68a5f78e8fb2ceab04aa719a6daf30a7999b0'

[[ -f "$ARTIFACTS_URL_PATH" ]] || {
    echo "Expected $ARTIFACTS_URL_PATH to exist"
    exit 1
}

# This is here to ensure that webhosting pipeline works
# Remove the job_id (this file would not exist in webhosting pipeline)
rm "$BOOK_DIR/_attic/IO_BOOK/job_id"
SKIP_DOCKER_BUILD=1 \
STUB_UPLOAD="webhosting" \
KCOV_DIR=_kcov03-c \
../enki --keep-data --data-dir $BOOK_DIR --command step-upload-book --repo 'philschatz/tiny-book' --ref '03e68a5f78e8fb2ceab04aa719a6daf30a7999b0'

[[ ! -f "$ARTIFACTS_URL_PATH" ]] || {
    echo "Did not expect $ARTIFACTS_URL_PATH to exist"
    exit 1
}

counter=0
while IFS=$'\n' read -r expected_contents; do
    counter=$((counter+1))
    actual_contents="$(cat $BOOK_DIR/_attic/IO_ARTIFACTS/upload_ancillaries_args_$counter)"
    if [[ "$expected_contents" != "$actual_contents" ]]; then
        echo "upload_ancillaries args."
        echo "Expected value: $expected_contents"
        echo "Actual value:   $actual_contents"
        exit 1
    fi
done <<EOF
/tmp/build/0000000/ancillary
EOF
# If you ever need to update the above list, just do `cat ../data/test-book/_attic/IO_ARTIFACTS/upload_ancillaries_args_*` and copy/paste :)

# Check local-preview works
SKIP_DOCKER_BUILD=1 \
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
CONTENT_SAMPLE_FILE="$(realpath $LOCAL_PREVIEW/contents/00000000-0000-0000-0000-000000000000@*:11111111-1111-4111-8111-111111111111.xhtml)"
[ -e "$CONTENT_SAMPLE_FILE" ] || local_preview_data_missing_halt "$CONTENT_SAMPLE_FILE content file missing"
grep -q "\<img src=\"..\/resources\/4e88fcaf0d07298343a7cb933926c4c0c6b5b017\"" "$CONTENT_SAMPLE_FILE" || local_preview_data_missing_halt "image content not found in content file"