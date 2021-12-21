parse_book_dir

pdf_filename=$(printf %s "$ARG_TARGET_PDF_FILENAME" | jq -sRr @uri) # URI-encode because book or branch name could have '#'
pdf_url="https://$ARG_S3_BUCKET_NAME.s3.amazonaws.com/$pdf_filename"

try echo -n "$pdf_url" > "$IO_ARTIFACTS/pdf_url"

echo "DONE: See book at $pdf_url"
