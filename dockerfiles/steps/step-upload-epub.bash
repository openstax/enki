parse_book_dir

set -Eeuo pipefail

{
    while read -r book_slug; do
        epub_file="$IO_ARTIFACTS/$book_slug.epub"
        [[ -f "$epub_file" ]] || die "Could not find \"$epub_file\""
        echo "$epub_file|$book_slug"
    done < <(read_book_slugs)  # LCOV_EXCL_LINE
} | sort | upload_book_artifacts "application/epub+zip"
