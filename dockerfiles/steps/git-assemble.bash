parse_book_dir

repo_root=$IO_FETCH_META
col_sep='|'
# https://stackoverflow.com/a/31838754
xpath_sel="//*[@slug]" # All the book entries
while read -r line; do # Loop over each <book> entry in the META-INF/books.xml manifest
    IFS=$col_sep read -r slug href _ <<< "$line"
    path="$repo_root/META-INF/$href"

    # ------------------------------------------
    # Available Variables: slug href style path
    # ------------------------------------------
    # --------- Code starts here



    try cp "$path" "$IO_FETCH_META/modules/collection.xml"

    if [[ -f temp-assembly/collection.assembled.xhtml ]]; then
        rm temp-assembly/collection.assembled.xhtml # LCOV_EXCL_LINE
    fi

    try neb assemble "$IO_FETCH_META/modules" temp-assembly/

    try cp "temp-assembly/collection.assembled.xhtml" "$IO_ASSEMBLED/$slug.assembled.xhtml"
    try rm -rf temp-assembly
    try rm "$IO_FETCH_META/modules/collection.xml"



    # --------- Code ends here
done < <(try xmlstarlet sel -t --match "$xpath_sel" --value-of '@slug' --value-of "'$col_sep'" --value-of '@href' --value-of "'$col_sep'" --value-of '@style' --nl < $repo_root/META-INF/books.xml)
