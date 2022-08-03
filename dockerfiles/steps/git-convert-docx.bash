# LCOV_EXCL_START
try pushd "$BAKERY_SCRIPTS_ROOT/scripts/"
try "$BAKERY_SCRIPTS_ROOT/scripts/node_modules/.bin/pm2" start mml2svg2png-json-rpc.js --node-args="-r esm" --wait-ready --listen-timeout 8000
try popd
try cp -r "$IO_GDOCIFIED/." "$IO_DOCX"
book_slugs_file="$(realpath "$IO_GDOCIFIED/book-slugs.json")"
book_dir="$(realpath "$IO_DOCX/content")"
target_dir="$(realpath "$IO_DOCX/docx")"
lang="$(cat "$IO_GDOCIFIED/language")"
reference_doc="$BAKERY_SCRIPTS_ROOT/scripts/gdoc/custom-reference-$lang.docx"
try mkdir -p "$target_dir"
try cd "$book_dir"

col_sep='|'
while read -r line; do
    IFS=$col_sep read -r slug uuid <<< "$line"
    current_target="$target_dir/$slug"
    [[ -d "$current_target" ]] || mkdir "$current_target"
    for xhtmlfile in ./"$uuid@"*.xhtml; do
        xhtmlfile_basename=$(basename "$xhtmlfile")
        metadata_filename="${xhtmlfile_basename%.*}"-metadata.json
        docx_filename=$(jq -r '.slug' "$metadata_filename").docx
        mathmltable_tempfile="$xhtmlfile.mathmltable.tmp"
        try mathmltable2png "$xhtmlfile" "../resources" "$mathmltable_tempfile"
        wrapped_tempfile="$xhtmlfile.greybox.tmp"

        say "Converting to docx: $xhtmlfile_basename"
        try xsltproc --output "$wrapped_tempfile" "$BAKERY_SCRIPTS_ROOT/scripts/gdoc/wrap-in-greybox.xsl" "$mathmltable_tempfile"
        try pandoc --fail-if-warnings --reference-doc="$reference_doc" --from=html --to=docx --output="$current_target/$docx_filename" "$wrapped_tempfile"
    done
done < <(try jq -r '.[] | .slug + "'$col_sep'" + .uuid' "$book_slugs_file")
try "$BAKERY_SCRIPTS_ROOT/scripts/node_modules/.bin/pm2" stop mml2svg2png-json-rpc
# LCOV_EXCL_STOP
