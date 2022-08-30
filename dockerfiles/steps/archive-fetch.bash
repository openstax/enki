parse_book_dir

temp_dir=$(mktemp -d)

set +E # The entrypoint script sets this to be -E which causes neb to fail
yes | try neb get -r -d "$temp_dir/does-not-exist-yet-dir" "$ARG_ARCHIVE_SERVER" "$ARG_COLLECTION_ID" "$ARG_COLLECTION_VERSION"
set -E

try mv $temp_dir/does-not-exist-yet-dir/* $IO_ARCHIVE_FETCHED
