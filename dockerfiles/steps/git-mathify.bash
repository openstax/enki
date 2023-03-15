parse_book_dir

# Style needed because mathjax will size converted math according to surrounding text
try cp "$IO_BAKED/the-style-pdf.css" "$IO_LINKED"
try cp "$IO_BAKED/the-style-pdf.css" "$IO_MATHIFIED"

shopt -s globstar nullglob
for collection in "$IO_LINKED/"*.linked.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')

    try node --max-old-space-size=8192 $MATHIFY_ROOT/typeset/start.js -i "$IO_LINKED/$slug_name.linked.xhtml" -o "$IO_MATHIFIED/$slug_name.mathified.xhtml" -f svg

done
shopt -u globstar nullglob
