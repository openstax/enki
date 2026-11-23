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

expected_contents="s3 cp artifacts-single/$expected_book_slug.$expected_extension s3://openstax-sandbox-cops-artifacts/$expected_filename --content-type $expected_mime_type"
actual_contents="$(cat $BOOK_DIR/_attic/IO_ARTIFACTS/aws_args_1)"
if [[ "$actual_contents" != "$expected_contents" ]]; then
    echo "Bad AWS CLI args."
    echo "Expected value: $expected_contents"
    echo "Actual value:   $actual_contents"
    exit 1
fi

# Test that step-pdf fails when an image has no Prince image box or has a zero-size box.
# Mutate the generated linked XHTML so these cases do not need a separate tiny-book branch.
pdf_linked_file="$BOOK_DIR/_attic/IO_LINKED/book-slug1.linked.xhtml"
pdf_linked_backup=$(mktemp)
cp "$pdf_linked_file" "$pdf_linked_backup"
restore_pdf_linked_file() {
    cp "$pdf_linked_backup" "$pdf_linked_file"
    rm -f "$pdf_linked_backup"
}
trap restore_pdf_linked_file EXIT

valid_image_src="$(sed -n 's/.*<img[^>]*src="\([^"]*\)".*/\1/p' "$pdf_linked_backup" | head -n 1)"
if [[ -z "$valid_image_src" ]]; then
    echo "Could not find a valid image source in $pdf_linked_file"
    exit 1
fi

set_pdf_image_case() {
    image_case="$1"
    awk -v image_case="$image_case" -v valid_image_src="$valid_image_src" -v linked_file="$pdf_linked_file" '
        !added && /<\/body>/ {
            if (image_case == "missing") {
                print "    <img src=\"../resources/check-images-test-missing-8e7c1f.png\" alt=\"missing image test\" />"
            } else {
                print "    <img src=\"" valid_image_src "\" alt=\"zero-size image test\" style=\"width: 0px; height: 0px;\" />"
            }
            added = 1
        }
        { print }
        END {
            if (!added) {
                print "Could not find the body element in " linked_file > "/dev/stderr"
                exit 1
            }
        }
    ' "$pdf_linked_backup" > "$pdf_linked_file"
}

expect_step_pdf_failure() {
    image_case="$1"
    if SKIP_DOCKER_BUILD=1 \
        ../enki --keep-data --data-dir "$BOOK_DIR" --command step-pdf --repo 'philschatz/tiny-book' --ref long-lived-branch-for-testing-with-#-char; then
        echo "Expected step-pdf to fail for the $image_case image case"
        exit 1
    fi
}

set_pdf_image_case missing
expect_step_pdf_failure missing

set_pdf_image_case zero-size
expect_step_pdf_failure zero-size

restore_pdf_linked_file
trap - EXIT

# Test without book slug
rm $BOOK_DIR/_attic/IO_BOOK/slugs
SKIP_DOCKER_BUILD=1 \
../enki --data-dir $BOOK_DIR --command step-pdf --repo 'philschatz/tiny-book' --ref long-lived-branch-for-testing-with-#-char

SKIP_DOCKER_BUILD=1 \
STUB_UPLOAD="corgi" \
../enki --keep-data --data-dir $BOOK_DIR --command step-upload-pdf
