parse_book_dir

shopt -s globstar nullglob
for collection in "$IO_BAKED/"*.baked.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')

    try-coverage /workspace/enki/venv/bin/link-single "$IO_BAKED" "$IO_BAKE_META" "$slug_name" "$IO_LINKED/$slug_name.linked.xhtml"

done
shopt -u globstar nullglob