parse_book_dir

# https://github.com/openstax/output-producer-service/blob/master/bakery/src/tasks/fetch-book.js#L38
temp_dir=$(mktemp -d)
yes | try neb get -r -d "$temp_dir/does-not-exist-yet-dir" "$ARG_ARCHIVE_SERVER" "$ARG_COLLECTION_ID" "$ARG_COLLECTION_VERSION"

try mv $temp_dir/does-not-exist-yet-dir/* $IO_ARCHIVE_FETCHED
