parse_book_dir
# TODO: Create an earlier task that downloads the ABL
book_slugs_url='https://raw.githubusercontent.com/openstax/content-manager-approved-books/master/approved-book-list.json'
try wget "$book_slugs_url" -O "/tmp/approved-book-list.json"


target_dir="$IO_REX_LINKED"
filename="$ARG_TARGET_SLUG_NAME.rex-linked.xhtml"
abl_file="/tmp/approved-book-list.json"
book_slugs_file="/tmp/book-slugs.json"
try cat $abl_file | jq ".approved_books|map(.books)|flatten" > "$book_slugs_file"

try link-rex "$IO_MATHIFIED/$ARG_TARGET_SLUG_NAME.mathified.xhtml" "$book_slugs_file" "$target_dir" "$filename"
