# Remove the mathified file if it already exists ecause the code assumes the file does not exist
[[ -f "$IO_ARCHIVE_BOOK/collection.mathified.xhtml" ]] && rm "$IO_ARCHIVE_BOOK/collection.mathified.xhtml"

try node $MATHIFY_ROOT/typeset/start.js -i "$IO_ARCHIVE_BOOK/collection.baked.xhtml" -o "$IO_ARCHIVE_BOOK/collection.mathified.xhtml" -f svg 
