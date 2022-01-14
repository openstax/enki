parse_book_dir

try jsonify "$IO_DISASSEMBLE_LINKED" "$IO_JSONIFIED"
manifest=$(cat "$IO_FETCH_META/books.xml.json")

shopt -s globstar nullglob
for collection in "$IO_JSONIFIED/"*.toc.json; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
    book_json_file="$IO_JSONIFIED/$slug_name.toc.json"
    books_json_append=$(jq -c '.book_json' <<< "$manifest")
    # Memorize book json file with cat before overwrite
    jq '. + '"$books_json_append" <<< $(cat $book_json_file) > $book_json_file

    try jsonschema -i "$IO_JSONIFIED/$slug_name.toc.json" $BAKERY_SCRIPTS_ROOT/scripts/book-schema-git.json

done
shopt -u globstar nullglob


for jsonfile in "$IO_JSONIFIED/"*@*.json; do
    try jsonschema -i "$jsonfile" $BAKERY_SCRIPTS_ROOT/scripts/page-schema.json
done
