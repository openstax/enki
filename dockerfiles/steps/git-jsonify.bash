parse_book_dir

function read_style() {
    slug_name=$1
    # Read from IO_BOOK/style if it exists
    if [ -e $IO_BOOK/style ]; then
        cat $IO_BOOK/style # LCOV_EXCL_LINE
    # Otherwise read from META-INF/books.xml
    else
        style_name=$(xmlstarlet sel -t --match "//*[@style][@slug=\"$slug_name\"]" --value-of '@style' < $IO_FETCHED/META-INF/books.xml)
        if [[ $style_name == '' ]]; then
            die "Book style was not in the META-INF/books.xml file and was not specified (if this was built via CORGI)" # LCOV_EXCL_LINE
        else
            echo "$style_name"
        fi
    fi
}

try jsonify "$IO_DISASSEMBLE_LINKED" "$IO_JSONIFIED"

repo_schema_version=$(try xmlstarlet sel -t -m '//*[@version]' -v '@version' < $IO_FETCHED/META-INF/books.xml)

shopt -s globstar nullglob
for collection in "$IO_JSONIFIED/"*.toc.json; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
    book_json_file="$IO_JSONIFIED/$slug_name.toc.json"
    style_name=$(read_style "$slug_name")
    # Glob here to avoid hardcoding web style file suffix
    style_file="$(ls -1 "$IO_RESOURCES/styles/$style_name"*.css)"
    # Die if the glob does not match exactly one file
    if [[ $(wc -l <<< "$style_file") != 1 ]]; then
        die "Could not find exact match for $style_name in IO_RESOURCES" # LCOV_EXCL_LINE
    fi
    style_href="resources/styles/$(basename $style_file)"
    books_json_append=$(jo repo_schema_version=$repo_schema_version style_name=$style_name style_href=$style_href)

    # Add our new information to the books json file, then overwrite the books json file
    try jq '. + '"$books_json_append" <<< "$(cat "$book_json_file")" > "$book_json_file"

    try jsonschema -i "$IO_JSONIFIED/$slug_name.toc.json" $BAKERY_SCRIPTS_ROOT/scripts/book-schema-git.json

done
shopt -u globstar nullglob


for jsonfile in "$IO_JSONIFIED/"*@*.json; do
    try jsonschema -i "$jsonfile" $BAKERY_SCRIPTS_ROOT/scripts/page-schema.json
done
