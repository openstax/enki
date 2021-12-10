# This /content/ subdir is necessary so that gdocify can resolve the relative path to the resources (../resources/{sha})
[[ -d $IO_ARCHIVE_GDOCIFIED/content ]] || mkdir $IO_ARCHIVE_GDOCIFIED/content
try cp -R $IO_ARCHIVE_BOOK/resources/. $IO_ARCHIVE_GDOCIFIED/resources

book_slugs_file="/tmp/book-slugs.json"
try cat "$IO_ARCHIVE_FETCHED/approved-book-list.json" | jq '[.approved_books[]|select(has("collection_id"))]|map(.books)|flatten' > "$book_slugs_file"
try gdocify "$IO_ARCHIVE_BOOK" "$IO_ARCHIVE_GDOCIFIED/content" "$book_slugs_file"
try cp "$IO_ARCHIVE_BOOK"/*@*-metadata.json "$IO_ARCHIVE_GDOCIFIED/content"
