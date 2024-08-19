parse_book_dir

set -Eeuo pipefail

cp -R "$IO_BAKED/downloaded-fonts" "/tmp"
mathml2png_rpc start
for book in "$IO_LINKED/"*.xhtml; do
    lang=en
    ref_doc="$BAKERY_SCRIPTS_ROOT/scripts/ppt/custom-reference-$lang.pptx"
    slug_name=$(basename "$book" | awk -F'[.]' '{ print $1; }')
    output_dir="$IO_PPTX/$slug_name"
    output_fmt="$output_dir/{slug}.{extension}"
    cover="$IO_FETCH_META/cover/$slug_name-cover.jpg"
    style="$IO_BAKED/$slug_name-pdf.css"
    mkdir -p "$output_dir"
    pptify "$book" "$IO_RESOURCES" "$ref_doc" "$cover" "$style" "$output_fmt"
done
mathml2png_rpc stop
