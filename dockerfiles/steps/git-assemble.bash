shopt -s globstar nullglob
for collection in "${IO_FETCH_META}/collections/"*; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
    if [[ -n "${ARG_OPT_ONLY_ONE_BOOK}" ]]; then
        [[ "$slug_name" != "${ARG_OPT_ONLY_ONE_BOOK}" ]] && continue # LCOV_EXCL_LINE
    fi
    try cp "$collection" "${IO_FETCH_META}/modules/collection.xml"

    try neb assemble "${IO_FETCH_META}/modules" temp-assembly/

    try cp "temp-assembly/collection.assembled.xhtml" "${IO_ASSEMBLED}/$slug_name.assembled.xhtml"
    try rm -rf temp-assembly
    try rm "${IO_FETCH_META}/modules/collection.xml"
done
shopt -u globstar nullglob
