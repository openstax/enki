# Formerly git-mathify
parse_book_dir

# Style needed because mathjax will size converted math according to surrounding text
cp "$IO_BAKED/the-style-pdf.css" "$IO_LINKED"
shopt -s globstar nullglob
for collection in "$IO_LINKED/"*.linked.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')

    node "${JS_EXTRA_VARS[@]}" $MATHIFY_ROOT/typeset/start.js -i "$IO_LINKED/$slug_name.linked.xhtml" -o "$IO_LINKED/$slug_name.mathified.xhtml" -h -f svg

done
shopt -u globstar nullglob


# Formerly git-link
parse_book_dir


target_dir="$IO_LINKED"
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
for collection in "$IO_LINKED/"*.mathified.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')

    link-rex "$IO_LINKED/$slug_name.mathified.xhtml" "$book_slugs_file" "$target_dir" "$slug_name.rex-linked.xhtml"

done
shopt -u globstar nullglob


# Formerly git-pdfify
parse_book_dir


while read -r slug; do
  if [[ -z "$slug" ]]; then break; fi
  prince -v --output="$IO_ARTIFACTS/$slug.pdf" "$slug.rex-linked.xhtml"
done < "$IO_BOOK/slugs"


# Verify the style file exists before building a PDF
# LCOV_EXCL_START
if [[ ! -f "$IO_LINKED/the-style-pdf.css" ]]; then
    say "=============================================="
    say " WARNING: There was no CSS file. Maybe a bug?"
    say " WARNING: Waiting 15 seconds"
    say "=============================================="
    sleep 15
fi
# LCOV_EXCL_STOP
