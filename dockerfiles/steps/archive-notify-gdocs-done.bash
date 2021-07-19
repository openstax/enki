# LCOV_EXCL_START
statePrefix='gdoc'
collection_id="$(cat $IO_BOOK/collection_id)"
book_legacy_version="$(cat $IO_BOOK/version)"
complete_filename=".$statePrefix.$collection_id@$book_legacy_version.complete"

try date -Iseconds > "/tmp/$complete_filename"
try aws s3 cp "/tmp/$complete_filename" "s3://$WEB_QUEUE_STATE_S3_BUCKET/$CODE_VERSION/$complete_filename"
# LCOV_EXCL_STOP
