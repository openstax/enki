parse_book_dir

try jsonify "$IO_DISASSEMBLE_LINKED" "$IO_JSONIFIED"
try jsonschema -i "$IO_JSONIFIED/$ARG_TARGET_SLUG_NAME.toc.json" $BAKERY_SCRIPTS_ROOT/scripts/book-schema-git.json

for jsonfile in "$IO_JSONIFIED/"*@*.json; do
    try jsonschema -i "$jsonfile" $BAKERY_SCRIPTS_ROOT/scripts/page-schema.json
done
