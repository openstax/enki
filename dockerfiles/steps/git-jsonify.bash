parse_book_dir

try jsonify "$IO_DISASSEMBLE_LINKED" "$IO_JSONIFIED"

repo_schema_version=$(try xmlstarlet sel -t -m '//*[@version]' -v '@version' < "$IO_FETCHED/META-INF/books.xml")

shopt -s globstar nullglob
for collection in "$IO_JSONIFIED/"*.toc.json; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
    book_json_file="$IO_JSONIFIED/$slug_name.toc.json"
    style_name=$(read_style "$slug_name")

    # Glob here to avoid hardcoding web style file suffix
    style_file=("$IO_RESOURCES/styles/$style_name"*.css)
    if [[ ${#style_file[@]} != 1 ]]; then
        die "Could not find exact match for $style_name in IO_RESOURCES" # LCOV_EXCL_LINE
    fi
    style_href="resources/styles/$(basename "${style_file[0]}")"

    book_json_append=$(jo repo_schema_version=$repo_schema_version style_name="$style_name" style_href="$style_href")
    # Add our new information to the books json file, then overwrite the books json file
    try jq '. + '"$book_json_append" <<< "$(cat "$book_json_file")" > "$book_json_file"

    try jsonschema -i "$IO_JSONIFIED/$slug_name.toc.json" $BAKERY_SCRIPTS_ROOT/scripts/book-schema-git.json

done
shopt -u globstar nullglob


for jsonfile in "$IO_JSONIFIED/"*@*.json; do
    try jsonschema -i "$jsonfile" $BAKERY_SCRIPTS_ROOT/scripts/page-schema.json
done
