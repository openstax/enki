parse_book_dir

commit_sha=$(cd "$IO_FETCHED" && git rev-parse HEAD)
version=${commit_sha:0:7}    # Use the first 7 characters of the sha because someone decided 7 was a lucky number

shopt -s globstar nullglob
for collection in "$IO_BAKED/"*.baked.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')

    try link-single "$IO_BAKED" "$IO_BAKE_META" "$slug_name" "$IO_LINKED/$slug_name.linked.xhtml" $version

done
shopt -u globstar nullglob