# Remove the rex-linked file if it already exists because the code assumes the file does not exist
[[ -f "$IO_ARCHIVE_BOOK/collection.rex-linked.xhtml" ]] && rm "$IO_ARCHIVE_BOOK/collection.rex-linked.xhtml"

target_dir="$IO_ARCHIVE_BOOK"
filename="collection.rex-linked.xhtml"
abl_file="$IO_ARCHIVE_FETCHED/approved-book-list.json"
book_slugs_file="/tmp/book-slugs.json"
try cat $abl_file | jq ".approved_books|map(.books)|flatten" > "$book_slugs_file"

try link-rex "$IO_ARCHIVE_BOOK/collection.mathified.xhtml" "$book_slugs_file" "$target_dir" "$filename"
