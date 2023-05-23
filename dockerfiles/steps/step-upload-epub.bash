# LCOV_EXCL_START
parse_book_dir

set -Eeuo pipefail

{
    for file_to_upload in "$IO_ARTIFACTS/"*.epub; do
        slug="$(basename "$file_to_upload" ".epub")"
        echo "$file_to_upload|$slug"
    done
} | sort | upload_book_artifacts "application/epub+zip"

# LCOV_EXCL_END
