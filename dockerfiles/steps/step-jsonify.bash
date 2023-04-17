parse_book_dir

jsonify "$IO_DISASSEMBLE_LINKED" "$IO_JSONIFIED"

repo_schema_version=$(xmlstarlet sel -t -m '//*[@version]' -v '@version' < "$IO_FETCHED/META-INF/books.xml")
style_resource_root="$IO_RESOURCES/styles"
generic_style="webview-generic.css"

shopt -s globstar nullglob
for collection in "$IO_JSONIFIED/"*.toc.json; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
    book_json_file="$IO_JSONIFIED/$slug_name.toc.json"
    style_name=$(read_style "$slug_name")

    # Glob here to avoid hardcoding web style file suffix
    style_file=("$style_resource_root/$style_name"*.css)
    styles_length=${#style_file[@]}
    if [[ $styles_length -gt 1 ]]; then # https://stackoverflow.com/a/69041782
        die "Could not find exact match for $style_name in IO_RESOURCES" # LCOV_EXCL_LINE
    elif [[ $styles_length -eq 1 && -f "${style_file[0]}" ]]; then
        style_filename="$(basename "${style_file[0]}")" # LCOV_EXCL_LINE
    else
        style_filename="$generic_style"
    fi

    book_json_append=$(jo repo_schema_version=$repo_schema_version style_name="$style_name" style_href="../resources/styles/$style_filename")
    # Add our new information to the books json file, then overwrite the books json file
    jq '. + '"$book_json_append" <<< "$(cat "$book_json_file")" > "$book_json_file"

    jsonschema -i "$IO_JSONIFIED/$slug_name.toc.json" $BAKERY_SCRIPTS_ROOT/scripts/book-schema-git.json

    # Parse the UUID and versions from the book metadata since it will be accessible
    # for any pipeline (web-hosting or web-preview) and to be self-consistent
    # metadata and values used.
    book_uuid=$(jq -r '.id' "$book_json_file")
    book_version=$(jq -r '.version' "$book_json_file")

    # Rename these files so local REX preview works
    cp "$IO_JSONIFIED/$slug_name.toc.json" "$IO_JSONIFIED/$book_uuid@$book_version.json.rex-preview"
    cp "$IO_JSONIFIED/$slug_name.toc.xhtml" "$IO_JSONIFIED/$book_uuid@$book_version.xhtml.rex-preview"

done
shopt -u globstar nullglob


for jsonfile in "$IO_JSONIFIED/"*@*:*.json; do
    jsonschema -i "$jsonfile" $BAKERY_SCRIPTS_ROOT/scripts/page-schema.json
done

# Formerly git-validate-xhtml-jsonify
do_xhtml_validate $IO_JSONIFIED "xhtml" duplicate-id 