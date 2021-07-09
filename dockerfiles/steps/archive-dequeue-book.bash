# LCOV_EXCL_START
CONTENT_SOURCE=archive

exec 2> >(tee $IO_BOOK/stderr >&2)
book="$S3_QUEUE/$ARG_CODE_VERSION.web-hosting-queue.json"
if [[ ! -s "$book" ]]; then
    echo "Book is empty"
    exit 1
fi

case $CONTENT_SOURCE in
    archive)
        echo -n "$(cat $book | jq -er '.collection_id')" >$IO_BOOK/collection_id
        echo -n "$(cat $book | jq -er '.server')" >$IO_BOOK/server
    ;;
    git)
        echo -n "$(cat $book | jq -r '.slug')" >$IO_BOOK/slug
        echo -n "$(cat $book | jq -r '.repo')" >$IO_BOOK/repo
    ;;
    *)
        echo "CONTENT_SOURCE unrecognized: $CONTENT_SOURCE"
        exit 1
    ;;
esac

echo -n "$(cat $book | jq -r '.style')" >$IO_BOOK/style
echo -n "$(cat $book | jq -r '.version')" >$IO_BOOK/version
echo -n "$(cat $book | jq -r '.uuid')" >$IO_BOOK/uuid
# LCOV_EXCL_STOP