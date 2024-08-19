# LCOV_EXCL_START
bucketPrefix=$STATE_PREFIX
codeVersion=$CODE_VERSION
queueStateBucket=$WEB_QUEUE_STATE_S3_BUCKET

book_id="$(cat $IO_BOOK/repo)"
version="$(cat $IO_BOOK/version)"
complete_filename=".$bucketPrefix.$book_id@$version.complete"
date -Iseconds > "/tmp/$complete_filename"

aws s3 cp "/tmp/$complete_filename" "s3://$queueStateBucket/$codeVersion/$complete_filename"
# LCOV_EXCL_STOP
