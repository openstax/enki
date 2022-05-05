# This /content/ subdir is necessary so that gdocify can resolve the relative path to the resources (../resources/{sha})
[[ -d $IO_GDOCIFIED/content ]] || mkdir $IO_GDOCIFIED/content
try cp -R $IO_RESOURCES/. $IO_GDOCIFIED/resources

book_slugs_file="/tmp/book-slugs.json"

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
try jo -a $jo_args > $book_slugs_file

# gdocify is tightly coupled to the archive format, use this dir to match it
tmp_book_dir="/tmp/archive-format"
[[ -d $tmp_book_dir ]] || mkdir $tmp_book_dir
try cp $IO_JSONIFIED/* $tmp_book_dir
try mv "$tmp_book_dir/$(cat $IO_BOOK/slug).toc.json" "$tmp_book_dir/collection.toc-metadata.json"
try cp $IO_DISASSEMBLE_LINKED/*@*-metadata.json $tmp_book_dir

try gdocify "$tmp_book_dir" "$IO_GDOCIFIED/content" "$book_slugs_file"
try cp "$tmp_book_dir"/*@*-metadata.json "$IO_GDOCIFIED/content"
