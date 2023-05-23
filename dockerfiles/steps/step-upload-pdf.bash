# LCOV_EXCL_START
parse_book_dir

set -Eeuo pipefail

{
    for file_to_upload in "$IO_ARTIFACTS/"*.pdf; do
        slug="$(basename "$file_to_upload" ".pdf")"
        echo "$file_to_upload|$slug"
    done
} | sort | upload_book_artifacts "application/pdf"

# LCOV_EXCL_END
