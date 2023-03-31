# Formerly git-disassemble
parse_book_dir

shopt -s globstar nullglob
for collection in "$IO_LINKED/"*.linked.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')

    disassemble "$IO_LINKED/$slug_name.linked.xhtml" "$IO_BAKE_META/$slug_name.baked-metadata.json" "$slug_name" "$IO_DISASSEMBLE_LINKED"

done
shopt -u globstar nullglob

# Formerly git-patch-disassembled-links
parse_book_dir

shopt -s globstar nullglob
for collection in "$IO_DISASSEMBLE_LINKED/"*.toc.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')

    patch-same-book-links "$IO_DISASSEMBLE_LINKED" "$IO_DISASSEMBLE_LINKED" "$slug_name"

done
shopt -u globstar nullglob
