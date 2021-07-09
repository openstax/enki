parse_book_dir

# Style needed because mathjax will size converted math according to surrounding text
try cp "${IO_BAKED}/the-style-pdf.css" "${IO_LINKED}"
try cp "${IO_BAKED}/the-style-pdf.css" "${IO_MATHIFIED}"
try node $MATHIFY_ROOT/typeset/start.js -i "${IO_LINKED}/$ARG_TARGET_SLUG_NAME.linked.xhtml" -o "${IO_MATHIFIED}/$ARG_TARGET_SLUG_NAME.mathified.xhtml" -f svg
