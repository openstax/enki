set -Eeuo pipefail

# Exclude because this is only used in upload. Granted, we may want to pick
# some parts out and include them in tests.
# LCOV_EXCL_START
repo_no_slashes="$(cat "$IO_BOOK/repo" | sed 's/\//-/g')"
zip_filename="$repo_no_slashes-$(cat "$IO_BOOK/version")-git-$(cat "$IO_BOOK/job_id")-docx.zip"
zip_filename="$(printf %s "$zip_filename" | jq -sRr @uri)"  # URI-encode because book or branch name could have '#'
zip_url="https://$ARG_S3_BUCKET_NAME.s3.amazonaws.com/$zip_filename"
zip_path="$(realpath "$IO_ARTIFACTS/$zip_filename")"

pushd "$IO_DOCX/docx"
zip -0r "$zip_path" ./*
popd

echo -n "$zip_url" > "$IO_ARTIFACTS/pdf_url"

echo "DONE: See book at $zip_url"
# LCOV_EXCL_STOP
