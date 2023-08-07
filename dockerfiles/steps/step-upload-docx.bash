parse_book_dir

set -Eeuo pipefail
{
    while read -r book_slug; do
        zip_path="$(realpath "$IO_ARTIFACTS/$book_slug.zip")"
        pushd "$IO_DOCX/docx" > /dev/null
        [[ -d "$book_slug" ]] || die "Could not find \"$book_slug\""
        >&2 zip -0r "$zip_path" "$book_slug"
        popd > /dev/null
        echo "$zip_path|$book_slug"
    done < <(read_book_slugs) # LCOV_EXCL_LINE
} | sort | upload_book_artifacts "application/zip" "$IO_ARTIFACTS"
