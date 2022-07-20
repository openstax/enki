zip_filename="$(cat "$IO_BOOK/repo")-$(cat "$IO_BOOK/version")-git-$(cat "$IO_BOOK/job_id")-docx.zip"
zip_filename="$(printf %s "$zip_filename" | jq -sRr @uri)"  # URI-encode because book or branch name could have '#'
zip_url="https://$ARG_S3_BUCKET_NAME.s3.amazonaws.com/$zip_filename"

try pushd "$IO_DOCX/docx"
try zip -0r "$IO_ARTIFACTS/$zip_filename" ./*
try popd

try echo -n "$zip_url" > "$IO_ARTIFACTS/pdf_url"

echo "DONE: See book at $zip_url"
