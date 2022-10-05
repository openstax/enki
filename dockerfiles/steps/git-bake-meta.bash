shopt -s globstar nullglob
for collection in "$IO_BAKED/"*.baked.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
    try-coverage /workspace/enki/venv/bin/bake-meta "$IO_ASSEMBLE_META/$slug_name.assembled-metadata.json" "$IO_BAKED/$slug_name.baked.xhtml" "" "" "$IO_BAKE_META/$slug_name.baked-metadata.json"
done
shopt -u globstar nullglob
