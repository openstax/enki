parse_book_dir
# TODO: Create an earlier task that downloads the ABL
book_slugs_url='https://raw.githubusercontent.com/openstax/content-manager-approved-books/master/approved-book-list.json'
try wget "$book_slugs_url" -O "/tmp/approved-book-list.json"


target_dir="$IO_REX_LINKED"
abl_file="/tmp/approved-book-list.json"
book_slugs_file="/tmp/book-slugs.json"
try cat $abl_file | jq '[.approved_books[]|select(has("collection_id"))]|map(.books)|flatten' > "$book_slugs_file"

shopt -s globstar nullglob
for collection in "$IO_MATHIFIED/"*.mathified.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')

    try link-rex "$IO_MATHIFIED/$slug_name.mathified.xhtml" "$book_slugs_file" "$target_dir" "$slug_name.rex-linked.xhtml"

done
shopt -u globstar nullglob


try cp "$IO_MATHIFIED/the-style-pdf.css" "$IO_REX_LINKED"
