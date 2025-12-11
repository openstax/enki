# Formerly git-mathify
parse_book_dir

# Style needed because mathjax will size converted math according to surrounding text
cp "$IO_BAKED/"*-pdf.css "$IO_LINKED"
cp -R "$IO_BAKED/downloaded-fonts" "$IO_LINKED"

target_dir="$IO_LINKED"
book_slugs_file="/tmp/book-slugs.json"

# Build a JSON array of uuid/slug pairs
# To do this we:
# 1. parse the slug & collection.xml href out of books.xml
# 1. parse the collection.xml file to extract the UUID
# 1. send the slug and uuid as args to jo (https://github.com/jpmens/jo)
jo_args=''

repo_root=$IO_FETCHED
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

xpath() {
    query="$1"
    path="$2"
    xmlstarlet sel -N 'x=http://www.w3.org/1999/xhtml' -t -m "$query" -v . -n "$path"
}

books_missing_styles=()
shopt -s globstar nullglob
while read -r book_slug; do
    mathified="$IO_LINKED/$book_slug.mathified.xhtml"
    node "${JS_EXTRA_VARS[@]}" $MATHIFY_ROOT/typeset/start.js -i "$IO_LINKED/$book_slug.linked.xhtml" -o "$mathified" -f svg
    [[ -f "$IO_LINKED/$book_slug-pdf.css" ]] || books_missing_styles+=("$book_slug")
    link-rex "$mathified" "$book_slugs_file" "$target_dir" "$book_slug.rex-linked.xhtml"
    print-customizations "$IO_LINKED/$book_slug.rex-linked.xhtml" "$IO_LINKED/$book_slug.print-ready.xhtml"
    cp "$IO_LINKED/$book_slug.rex-linked.xhtml" "$IO_LINKED/$book_slug.print-ready.xhtml"

    title="$(xpath '/x:html/x:head/x:title/text()' "$mathified")"
    language="$(xpath '/x:html/x:head/x:meta[@data-type="language"]/@content' "$mathified")"
    prince --pdf-title "${title:?}" --pdf-lang "${language:?}" --tagged-pdf --pdf-profile PDF/UA-1 --output="$IO_ARTIFACTS/$book_slug.pdf" -v "$IO_LINKED/$book_slug.print-ready.xhtml"
done < <(jq -r '.[].slug' "$book_slugs_file")
shopt -u globstar nullglob

# Warn about missing styles (prince does not care)
# LCOV_EXCL_START
if [[ ${#books_missing_styles[@]} -gt 0 ]]; then
    say "=============================================="
    say " WARNING: Missing CSS files for these books:"
    say " WARNING: ${books_missing_styles[*]}"
    say " WARNING: Maybe a bug?"
    say " WARNING: Waiting 15 seconds"
    say "=============================================="
    sleep 15
fi
# LCOV_EXCL_STOP
