shopt -s globstar nullglob
# Create an empty map file for invoking assemble-meta
echo "{}" > uuid-to-revised-map.json
for collection in "$IO_ASSEMBLED/"*.assembled.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
    if [[ -n "$ARG_OPT_ONLY_ONE_BOOK" ]]; then
        [[ "$slug_name" != "$ARG_OPT_ONLY_ONE_BOOK" ]] && continue # LCOV_EXCL_LINE
    fi
    try assemble-meta "$IO_ASSEMBLED/$slug_name.assembled.xhtml" uuid-to-revised-map.json "$IO_ASSEMBLE_META/$slug_name.assembled-metadata.json"
done
try rm uuid-to-revised-map.json
shopt -u globstar nullglob
