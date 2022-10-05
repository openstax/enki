parse_book_dir

shopt -s globstar nullglob
for collection in "$IO_DISASSEMBLED/"*.toc.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')

    try-coverage /workspace/enki/venv/bin/patch-same-book-links "$IO_DISASSEMBLED" "$IO_DISASSEMBLE_LINKED" "$slug_name"
    try cp "$IO_DISASSEMBLED"/"$slug_name".toc* "$IO_DISASSEMBLE_LINKED"

done
shopt -u globstar nullglob

try cp "$IO_DISASSEMBLED"/*@*-metadata.json "$IO_DISASSEMBLE_LINKED"
