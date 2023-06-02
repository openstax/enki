# Formerly git-bake-meta
shopt -s globstar nullglob
for collection in "$IO_BAKED/"*.baked.xhtml; do
    if grep -E '.*data-math=.+?' "$collection" &> /dev/null; then
        mathified="$collection.mathified.xhtml"
        node "${JS_EXTRA_VARS[@]}" $MATHIFY_ROOT/typeset/start.js -i "$collection" -o "$mathified" -f mathml
        mv "$mathified" "$collection"
    fi
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
    bake-meta "$IO_ASSEMBLE_META/$slug_name.assembled-metadata.json" "$IO_BAKED/$slug_name.baked.xhtml" "" "" "$IO_BAKE_META/$slug_name.baked-metadata.json"
done
shopt -u globstar nullglob

# Formerly git-link
parse_book_dir

commit_sha=$(cd "$IO_FETCHED" && git rev-parse HEAD)
version=${commit_sha:0:7}    # Use the first 7 characters of the sha because someone decided 7 was a lucky number

shopt -s globstar nullglob
for collection in "$IO_BAKED/"*.baked.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')

    link-single "$IO_BAKED" "$IO_BAKE_META" "$slug_name" "$IO_LINKED/$slug_name.linked.xhtml" $version

done
shopt -u globstar nullglob