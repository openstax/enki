# LCOV_EXCL_START
CONTENT_SOURCE=archive
bucketPrefix=archive-dist
codeVersion=$CODE_VERSION
queueStateBucket=$WEB_QUEUE_STATE_S3_BUCKET

case $CONTENT_SOURCE in
archive)
    book_id="$(cat $IO_BOOK/collection_id)"
    ;;
git)
    book_id="$(cat $IO_BOOK/slug)"
    ;;
*)
    echo "CONTENT_SOURCE unrecognized: $CONTENT_SOURCE"
    exit 1
    ;;
esac
            
version="$(cat $IO_BOOK/version)"
complete_filename=".${bucketPrefix}.$book_id@$version.complete"
try date -Iseconds > "/tmp/$complete_filename"

try aws s3 cp "/tmp/$complete_filename" "s3://${queueStateBucket}/${codeVersion}/$complete_filename"
# LCOV_EXCL_STOP
