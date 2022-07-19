parse_book_dir

pdf_filename=$(printf %s "$ARG_TARGET_PDF_FILENAME" | jq -sRr @uri) # URI-encode because book or branch name could have '#'
zip_filename=$(echo "$pdf_filename" | awk -F '.' '{ print $1"-docx.zip" }')
zip_url="https://$ARG_S3_BUCKET_NAME.s3.amazonaws.com/$zip_filename"

try pushd "$IO_DOCX/docx"
try zip -0r "$IO_ARTIFACTS/$zip_filename" ./*
try popd

try echo -n "$zip_url" > "$IO_ARTIFACTS/pdf_url"

echo "DONE: See book at $zip_url"
