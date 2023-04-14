parse_book_dir


target_dir="$IO_REX_LINKED"
book_slugs_file="/tmp/book-slugs.json"

# Build a JSON array of uuid/slug pairs
# To do this we:
# 1. parse the slug & collection.xml href out of books.xml
# 1. parse the collection.xml file to extract the UUID
# 1. send the slug and uuid as args to jo (https://github.com/jpmens/jo)
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
done < <(xmlstarlet sel -t --match "$xpath_sel" --value-of '@slug' --value-of "'$col_sep'" --value-of '@href' --value-of "'$col_sep'" --value-of '@style' --nl < $repo_root/META-INF/books.xml)

# Save all the slug/uuid pairs into a JSON file
jo -a $jo_args > $book_slugs_file

shopt -s globstar nullglob
for collection in "$IO_MATHIFIED/"*.mathified.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')

    link-rex "$IO_MATHIFIED/$slug_name.mathified.xhtml" "$book_slugs_file" "$target_dir" "$slug_name.rex-linked.xhtml"

done
shopt -u globstar nullglob


cp "$IO_MATHIFIED/the-style-pdf.css" "$IO_REX_LINKED"
