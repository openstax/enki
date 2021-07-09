target_dir="$IO_ARCHIVE_JSONIFIED"

try mkdir -p $target_dir
try jsonify "$IO_ARCHIVE_BOOK" "$target_dir"
try cp "$target_dir/collection.toc.json" "$IO_ARTIFACTS/"
try jsonschema -i "$target_dir/collection.toc.json" $BAKERY_SCRIPTS_ROOT/scripts/book-schema.json
for jsonfile in "$target_dir/"*@*.json; do
    #ignore -metadata.json files
    if [[ $jsonfile != *-metadata.json ]]; then
        try jsonschema -i "$jsonfile" $BAKERY_SCRIPTS_ROOT/scripts/page-schema.json
    fi
done
