# This /content/ subdir is necessary so that gdocify can resolve the relative path to the resources (../resources/{sha})
[[ -d "$IO_GDOCIFIED/content" ]] || mkdir "$IO_GDOCIFIED/content"
try cp -R "$IO_RESOURCES/." "$IO_GDOCIFIED/resources"

book_slugs_file="$IO_GDOCIFIED/book-slugs.json"

jo_args=''

repo_root=$IO_FETCH_META
col_sep='|'
xpath_sel="//*[@slug]" # All the book entries
while read -r line; do # Loop over each <book> entry in the META-INF/books.xml manifest
    IFS=$col_sep read -r slug href _ <<< "$line"
    path="$repo_root/META-INF/$href"

    # ------------------------------------------
    # Available Variables: slug href style path
    # ------------------------------------------
    # --------- Code starts here


    # Extract the UUID out of the collection.xml file. Ideally this might be better to have in books.xml directly.
    uuid=$(xmlstarlet sel -t --match "//*[local-name()='uuid']" --value-of 'text()' < $path)
    jo_args="$jo_args $(jo slug=$slug uuid=$uuid)"


    # --------- Code ends here
done < <(try xmlstarlet sel -t --match "$xpath_sel" --value-of '@slug' --value-of "'$col_sep'" --value-of '@href' --value-of "'$col_sep'" --value-of '@style' --nl < $repo_root/META-INF/books.xml)

# Save all the slug/uuid pairs into a JSON file
# NOTE: This file is also used in convert-docx
try jo -a $jo_args > "$book_slugs_file"

try gdocify "$IO_JSONIFIED" "$IO_GDOCIFIED/content" "$book_slugs_file"
try cp "$IO_DISASSEMBLE_LINKED"/*@*-metadata.json "$IO_GDOCIFIED/content"

lang="$(try jq -r '.language' "$IO_JSONIFIED/"*.toc.json | uniq)"
# If there was more than one result from uniq, there were different languages
if [[ $(wc -l <<< "$lang") != 1 ]]; then
    die "Language mismatch between book slugs."  # LCOV_EXCL_LINE
fi
echo "$lang" > "$IO_GDOCIFIED/language"
