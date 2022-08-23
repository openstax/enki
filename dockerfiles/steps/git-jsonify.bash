parse_book_dir

try jsonify "$IO_DISASSEMBLE_LINKED" "$IO_JSONIFIED"

repo_schema_version=$(try xmlstarlet sel -t -m '//*[@version]' -v '@version' < "$IO_FETCHED/META-INF/books.xml")
style_resource_root="$IO_RESOURCES/styles"
generic_style="webview-generic.css"

shopt -s globstar nullglob
for collection in "$IO_JSONIFIED/"*.toc.json; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
    book_json_file="$IO_JSONIFIED/$slug_name.toc.json"
    style_name=$(read_style "$slug_name")

    # Glob here to avoid hardcoding web style file suffix
    style_file=("$style_resource_root/$style_name"*.css)
    if [[ ${#style_file[@]} != 0 ]]; then

        style_filename="$(basename "${style_file[0]}")"
        if [[ ${#style_file[@]} -gt 1 ]]; then
            die "Could not find exact match for $style_name in IO_RESOURCES" # LCOV_EXCL_LINE
        elif [[ ! -f "${style_file[0]}" ]]; then
            style_filename="$generic_style"
        fi
    else
        style_filename="$generic_style"
    fi

    book_json_append=$(jo repo_schema_version=$repo_schema_version style_name="$style_name" style_href="../resources/styles/$style_filename")
    # Add our new information to the books json file, then overwrite the books json file
    try jq '. + '"$book_json_append" <<< "$(cat "$book_json_file")" > "$book_json_file"

    try jsonschema -i "$IO_JSONIFIED/$slug_name.toc.json" $BAKERY_SCRIPTS_ROOT/scripts/book-schema-git.json

done
shopt -u globstar nullglob


for jsonfile in "$IO_JSONIFIED/"*@*.json; do
    try jsonschema -i "$jsonfile" $BAKERY_SCRIPTS_ROOT/scripts/page-schema.json
done
