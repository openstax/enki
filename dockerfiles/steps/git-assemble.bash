set -Eeuo pipefail

parse_book_dir

cp -r "$IO_INITIAL_RESOURCES/." "$IO_RESOURCES"

repo_root=$IO_FETCH_META


if [[ $LOCAL_ATTIC_DIR != '' ]]; then
    echo 'Annotating XML files with source map information (data-sm="...")'
    pushd $IO_FETCH_META > /dev/null
    files=$(find . -name '*.cnxml' -or -name '*.collection.xml')
    for file in $files; do
        node --unhandled-rejections=strict "$JS_UTILS_STUFF_ROOT/bin/bakery-helper" add-sourcemap-info "$file" "$file"
    done
    popd > /dev/null
fi

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



    cp "$path" "$IO_FETCH_META/modules/collection.xml"

    if [[ -f temp-assembly/collection.assembled.xhtml ]]; then
        rm temp-assembly/collection.assembled.xhtml # LCOV_EXCL_LINE
    fi

    echo "Assembling '$slug'..."
    neb assemble "$IO_FETCH_META/modules" temp-assembly/

    ## download exercise images and replace internet links with local resource links
    download-exercise-images "$IO_RESOURCES" "temp-assembly/collection.assembled.xhtml" "$IO_ASSEMBLED/$slug.assembled.xhtml"

    rm -rf temp-assembly
    rm "$IO_FETCH_META/modules/collection.xml"



    # --------- Code ends here
done < <(xmlstarlet sel -t --match "$xpath_sel" --value-of '@slug' --value-of "'$col_sep'" --value-of '@href' --value-of "'$col_sep'" --value-of '@style' --nl < $repo_root/META-INF/books.xml)
