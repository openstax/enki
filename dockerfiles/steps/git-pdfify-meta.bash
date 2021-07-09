parse_book_dir

pdf_url="https://${ARG_S3_BUCKET_NAME}.s3.amazonaws.com/${ARG_TARGET_PDF_FILENAME}"
try echo -n "${pdf_url}" > "${IO_ARTIFACTS}/pdf_url"

echo "DONE: See book at ${pdf_url}"
