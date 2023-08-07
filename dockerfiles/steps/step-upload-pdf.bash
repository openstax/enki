parse_book_dir

set -Eeuo pipefail

{
    while read -r book_slug; do
        pdf_file="$IO_ARTIFACTS/$book_slug.pdf"
        [[ -f "$pdf_file" ]] || die "Could not find \"$pdf_file\""
        echo "$pdf_file|$book_slug"
    done < <(read_book_slugs)  # LCOV_EXCL_LINE
} | sort | upload_book_artifacts "application/pdf" "$IO_ARTIFACTS"
