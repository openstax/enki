#!/bin/bash
set -e
[[ $TRACE_ON ]] && set -x
[[ $0 != "-bash" ]] && cd "$(dirname "$0")"


BOOK_DIR=../data/test-book

# Test from the start with book slug
SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov03-a \
../enki --keep-data --data-dir $BOOK_DIR --command all-web --repo 'philschatz/tiny-book' --book-slug 'book-slug1' --ref '9044eef59f74f425d017ca574f40cce7350a9918'

SKIP_DOCKER_BUILD=1 \
STUB_UPLOAD=1 \
KCOV_DIR=_kcov03-b \
../enki --keep-data --data-dir $BOOK_DIR --command step-upload-book --repo 'philschatz/tiny-book' --book-slug 'book-slug1' --ref '9044eef59f74f425d017ca574f40cce7350a9918'

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
done < <(cat <<EOF
s3 cp --recursive /data/artifacts-single s3://openstax-sandbox-cops-artifacts/apps/archive-localdev/test/contents
s3 cp --recursive /data/resources/interactives-thisnamedoesnotmatter/ s3://openstax-sandbox-cops-artifacts/apps/archive-localdev/test/resources/interactives-thisnamedoesnotmatter
s3 cp --recursive /data/resources/styles/ s3://openstax-sandbox-cops-artifacts/apps/archive-localdev/test/resources/styles
s3 cp /data/jsonified-single/book-slug1.toc.json s3://openstax-sandbox-cops-artifacts/apps/archive-localdev/test/contents/00000000-0000-0000-0000-000000000000@9044eef.json
s3 cp /data/jsonified-single/book-slug1.toc.xhtml s3://openstax-sandbox-cops-artifacts/apps/archive-localdev/test/contents/00000000-0000-0000-0000-000000000000@9044eef.xhtml
EOF
)
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
done < <(cat <<EOF
/data/resources openstax-sandbox-cops-artifacts apps/archive-localdev/test/resources
EOF
)
# If you ever need to update the above list, just do `cat ../data/test-book/_attic/IO_ARTIFACTS/copy_resources_s3_args_*` and copy/paste :)


# Test without book slug
rm $BOOK_DIR/_attic/IO_BOOK/slugs
SKIP_DOCKER_BUILD=1 \
../enki --data-dir $BOOK_DIR --command all-web --start-at step-disassemble --repo 'philschatz/tiny-book' --ref '9044eef59f74f425d017ca574f40cce7350a9918'

SKIP_DOCKER_BUILD=1 \
STUB_UPLOAD=1 \
../enki --keep-data --data-dir $BOOK_DIR --command step-upload-book --repo 'philschatz/tiny-book' --ref '9044eef59f74f425d017ca574f40cce7350a9918'


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