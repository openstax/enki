parse_book_dir

set -Eeuxo pipefail

# Ensure $IO_EPUB is empty
[[ -d $IO_EPUB ]] && rm -rf ${IO_EPUB:?}/*

try node --unhandled-rejections=strict "$JS_UTILS_STUFF_ROOT/bin/bakery-helper" epub ./ "$IO_EPUB/"

shopt -s globstar nullglob
for book_dir in "$IO_EPUB/"*; do

    slug_name=$(basename "$book_dir")
    # Paths are relative in concourse.
    # Make this path absolute before changing directories
    epub_file_path="$(realpath "$IO_ARTIFACTS/$slug_name.epub")"
    pushd "$book_dir"
    zip "$epub_file_path" -DX0 mimetype
    zip "$epub_file_path" -DX9 META-INF/container.xml
    zip "$epub_file_path" -DX9 ./*
    popd

done


# Prepare for upload
repo_no_slashes="$(cat "$IO_BOOK/repo" | sed 's/\//-/g')"
zip_filename="$repo_no_slashes-$(cat "$IO_BOOK/version")-git-$(cat "$IO_BOOK/job_id")-epub.zip"
zip_filename="$(printf %s "$zip_filename" | jq -sRr @uri)"  # URI-encode because book or branch name could have '#'
zip_url="https://$ARG_S3_BUCKET_NAME.s3.amazonaws.com/$zip_filename"
zip_path="$(realpath "$IO_ARTIFACTS/$zip_filename")"

# Move into IO_ARTIFACTS so that the contents are in the root of the zip file
try pushd "$IO_ARTIFACTS"
try zip -0 "$zip_path" ./*.epub
try popd

# This is used to communicate the link to CORGI
try echo -n "$zip_url" > "$IO_ARTIFACTS/pdf_url"

shopt -u globstar nullglob
