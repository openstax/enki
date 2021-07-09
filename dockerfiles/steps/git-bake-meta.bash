shopt -s globstar nullglob
for collection in "${IO_BAKED}/"*.baked.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
    if [[ -n "${ARG_OPT_ONLY_ONE_BOOK}" ]]; then
        [[ "$slug_name" != "${ARG_OPT_ONLY_ONE_BOOK}" ]] && continue # LCOV_EXCL_LINE
    fi

    try bake-meta "${IO_ASSEMBLE_META}/$slug_name.assembled-metadata.json" "${IO_BAKED}/$slug_name.baked.xhtml" "" "" "${IO_BAKE_META}/$slug_name.baked-metadata.json"
done
shopt -u globstar nullglob
