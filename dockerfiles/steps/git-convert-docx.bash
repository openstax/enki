set -Eeuo pipefail

# LCOV_EXCL_START
pushd "$BAKERY_SCRIPTS_ROOT/scripts/"
"$BAKERY_SCRIPTS_ROOT/scripts/node_modules/.bin/pm2" start mml2svg2png-json-rpc.js --node-args="-r esm" --wait-ready --listen-timeout 8000
popd
cp -r "$IO_GDOCIFIED/." "$IO_DOCX"
book_slugs_file="$(realpath "$IO_GDOCIFIED/book-slugs.json")"
book_dir="$(realpath "$IO_DOCX/content")"
target_dir="$(realpath "$IO_DOCX/docx")"
lang="$(cat "$IO_GDOCIFIED/language")"
reference_doc="$BAKERY_SCRIPTS_ROOT/scripts/gdoc/custom-reference-$lang.docx"
mkdir -p "$target_dir"
cd "$book_dir"

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
        mathmltable2png "$xhtmlfile" "../resources" "$mathmltable_tempfile"
        wrapped_tempfile="$xhtmlfile.greybox.tmp"

        say "Converting to docx: $xhtmlfile_basename"
        xsltproc --output "$wrapped_tempfile" "$BAKERY_SCRIPTS_ROOT/scripts/gdoc/wrap-in-greybox.xsl" "$mathmltable_tempfile"
        pandoc --fail-if-warnings --reference-doc="$reference_doc" --from=html --to=docx --output="$current_target/$docx_filename" "$wrapped_tempfile"
    done
done < <(jq -r '.[] | .slug + "'$col_sep'" + .uuid' "$book_slugs_file")
"$BAKERY_SCRIPTS_ROOT/scripts/node_modules/.bin/pm2" stop mml2svg2png-json-rpc
# LCOV_EXCL_STOP
