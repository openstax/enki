parse_book_dir

set -Eeuo pipefail

mathml2png_rpc start
for collection in "$IO_LINKED/"*.xhtml; do
    lang=en
    reference_doc="$BAKERY_SCRIPTS_ROOT/scripts/ppt/custom-reference-$lang.pptx"
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
    output_dir="$IO_PPTX/$slug_name"
    output_fmt="$output_dir/{slug}.{extension}"
    mkdir -p "$output_dir"
    pptify \
        "$collection" \
        "$IO_RESOURCES" \
        "$reference_doc" \
        "$IO_FETCH_META/cover/$slug_name-cover.jpg" \
        "$IO_BAKED/$slug_name-pdf.css" \
        "$output_fmt"
done
mathml2png_rpc stop
