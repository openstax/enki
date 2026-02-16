parse_book_dir

set -Eeuo pipefail

cp -R "$IO_BAKED/downloaded-fonts" "/tmp"
mathml2png_rpc start
for book in "$IO_LINKED/"*.xhtml; do
    slug_name=$(basename "$book" | awk -F'[.]' '{ print $1; }')
    collection_file="$IO_FETCH_META/collections/$slug_name.collection.xml"
    lang=$(xmlstarlet sel -t -m '//*[local-name() = "language"]/text()' -v . -n "$collection_file" || { warn "Failed to find language" >&2; echo "en"; })
    ref_doc="$BAKERY_SCRIPTS_ROOT/scripts/ppt/custom-reference-$lang.pptx"
    # LCOV_EXCL_START
    if [[ ! -f "$ref_doc" ]]; then
        warn "No PPT template for language '$lang', falling back to English"
        ref_doc="$BAKERY_SCRIPTS_ROOT/scripts/ppt/custom-reference-en.pptx"
    fi
    # LCOV_EXCL_END
    output_dir="$IO_PPTX/$slug_name"
    output_fmt="$output_dir/{slug}.{extension}"
    cover="$IO_FETCH_META/cover/$slug_name-cover.jpg"
    style="$IO_BAKED/$slug_name-pdf.css"
    mkdir -p "$output_dir"
    pptify "$book" "$IO_RESOURCES" "$ref_doc" "$cover" "$style" "$output_fmt" "$lang"
done
mathml2png_rpc stop
