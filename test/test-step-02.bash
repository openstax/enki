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
            print "<!-- HACK: injected math and code -->"
            print "<div id=\"math-element\" data-math=\"\\frac{2}{5} + \\frac{10}{5}\"></div>"
            print "<code id=\"code-element\" data-lang=\"python\">hello = 5</code>"
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

# Check that the math and code are converted
while read -r assembled_file; do
    if ! grep '<math xmlns="http://www.w3.org/1998/Math/MathML" alttext="\\frac{2}{5} + \\frac{10}{5}">' "$assembled_file" &> /dev/null; then
        echo "ERROR: Could not find converted math"
        exit 1
    fi
    if ! grep -E '<pre data-type="code" .*data-lang="python".*>hello = <span class="hljs-number">5</span></pre>' "$assembled_file" &> /dev/null; then
        echo "ERROR: Could not find converted code element"
        exit 1
    fi
done < <(find $BOOK_DIR -name '*.assembled.xhtml') 

# ################################
# Clone a branch, 
# 'upload' the PDF,
# and verify the awscli arguments
# ################################

SKIP_DOCKER_BUILD=1 \
../enki --keep-data --data-dir $BOOK_DIR --command all-pdf --repo 'philschatz/tiny-book' --book-slug 'book-slug1' --ref long-lived-branch-for-testing-with-#-char

SKIP_DOCKER_BUILD=1 \
KCOV_DIR=_kcov02-e \
STUB_UPLOAD="corgi" \
../enki --keep-data --data-dir $BOOK_DIR --command step-upload-pdf

expected_repo="philschatz-tiny-book"
expected_version="long-lived-branch-for-testing-with-#-char"
expected_version_url_encd="long-lived-branch-for-testing-with-%23-char"
expected_job_id="-123456"
expected_book_slug="book-slug1"
expected_extension="pdf"
expected_mime_type="application/pdf"
expected_filename="$expected_repo-$expected_version-$expected_job_id-$expected_book_slug.$expected_extension"
expected_filename_url_encd="$expected_repo-$expected_version_url_encd-$expected_job_id-$expected_book_slug.$expected_extension"
# CORGI should get a url encoded file name; aws cli should get a raw file name
expected_contents='[{"url":"https://openstax-sandbox-cops-artifacts.s3.amazonaws.com/'"$expected_filename_url_encd"'","slug":"'"$expected_book_slug"'"}]'
actual_contents="$(cat $BOOK_DIR/_attic/IO_ARTIFACTS/artifact_urls.json)"
if [[ "$actual_contents" != "$expected_contents" ]]; then
    echo "Bad artifact urls."
    echo "Expected value: $expected_contents"
    echo "Actual value:   $actual_contents"
    exit 1
fi

expected_contents="s3 cp /tmp/build/0000000/artifacts-single/$expected_book_slug.$expected_extension s3://openstax-sandbox-cops-artifacts/$expected_filename --content-type $expected_mime_type"
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
../enki --data-dir $BOOK_DIR --command step-pdf --repo 'philschatz/tiny-book' --ref long-lived-branch-for-testing-with-#-char

SKIP_DOCKER_BUILD=1 \
STUB_UPLOAD="corgi" \
../enki --keep-data --data-dir $BOOK_DIR --command step-upload-pdf