parse_book_dir

shopt -s globstar nullglob
for collection in "$IO_LINKED/"*.linked.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')

    try disassemble "$IO_LINKED/$slug_name.linked.xhtml" "$IO_BAKE_META/$slug_name.baked-metadata.json" "$slug_name" "$IO_DISASSEMBLED"

done
shopt -u globstar nullglob
