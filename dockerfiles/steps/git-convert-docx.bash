# LCOV_EXCL_START
try pushd $BAKERY_SCRIPTS_ROOT/scripts/
try $BAKERY_SCRIPTS_ROOT/scripts/node_modules/.bin/pm2 start mml2svg2png-json-rpc.js --node-args="-r esm" --wait-ready --listen-timeout 8000
try popd
try cp -r $IO_GDOCIFIED/. $IO_DOCX
book_dir="$IO_DOCX/content"
target_dir="$IO_DOCX/docx"
try mkdir -p "$target_dir"
try cd "$book_dir"
for xhtmlfile in ./*@*.xhtml; do
    xhtmlfile_basename=$(basename "$xhtmlfile")
    metadata_filename="${xhtmlfile_basename%.*}"-metadata.json
    docx_filename=$(cat "$metadata_filename" | jq -r '.slug').docx
    mathmltable_tempfile="$xhtmlfile.mathmltable.tmp"
    try mathmltable2png "$xhtmlfile" "../resources" "$mathmltable_tempfile"
    wrapped_tempfile="$xhtmlfile.greybox.tmp"
    
    say "Converting to docx: $xhtmlfile_basename"
    try xsltproc --output "$wrapped_tempfile" $BAKERY_SCRIPTS_ROOT/scripts/gdoc/wrap-in-greybox.xsl "$mathmltable_tempfile"
    try pandoc --reference-doc="$BAKERY_SCRIPTS_ROOT/scripts/gdoc/custom-reference.docx" --from=html --to=docx --output="../../../$target_dir/$docx_filename" "$wrapped_tempfile"
done
try $BAKERY_SCRIPTS_ROOT/scripts/node_modules/.bin/pm2 stop mml2svg2png-json-rpc
# LCOV_EXCL_STOP
