parse_book_dir

try prince -v --output="$IO_ARTIFACTS/$ARG_TARGET_PDF_FILENAME" "$IO_REX_LINKED/$ARG_TARGET_SLUG_NAME.rex-linked.xhtml"

# Verify the style file exists before building a PDF
# LCOV_EXCL_START
if [[ ! -f "$IO_REX_LINKED/the-style-pdf.css" ]]; then
    say "=============================================="
    say " WARNING: There was no CSS file. Maybe a bug?"
    say " WARNING: Waiting 15 seconds"
    say "=============================================="
    try sleep 15
fi
# LCOV_EXCL_STOP
