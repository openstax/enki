# LCOV_EXCL_START
set +x
echo "$GOOGLE_SERVICE_ACCOUNT_CREDENTIALS" > /tmp/service_account_credentials.json
# Secret credentials above, do not use set -x above this line.
[[ $TRACE_ON ]] && set -x

docx_dir="$IO_ARCHIVE_DOCX/docx"
book_metadata="$IO_ARCHIVE_FETCHED/metadata.json"
book_title="$(cat $book_metadata | jq -r '.title')"
try upload-docx "$docx_dir" "$book_title" "${GDOC_GOOGLE_FOLDER_ID}" /tmp/service_account_credentials.json
# LCOV_EXCL_STOP
