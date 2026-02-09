# Formerly git-gdocify

# This /content/ subdir is necessary so that gdocify can resolve the relative path to the resources (../resources/{sha})
[[ -d "$IO_DOCX/content" ]] || mkdir "$IO_DOCX/content"
cp -R "$IO_RESOURCES/." "$IO_DOCX/resources"

book_slugs_file="$IO_DOCX/book-slugs.json"

jo_args=''

repo_root=$IO_FETCHED
col_sep='|'
xpath_sel="//*[@slug]" # All the book entries
while read -r line; do # Loop over each <book> entry in the META-INF/books.xml manifest
    IFS=$col_sep read -r slug href _ <<< "$line"
    path="$repo_root/META-INF/$href"

    # ------------------------------------------
    # Available Variables: slug href style path
    # ------------------------------------------
    # --------- Code starts here


    # Extract the UUID out of the collection.xml file. Ideally this might be better to have in books.xml directly.
    uuid=$(xmlstarlet sel -t --match "//*[local-name()='uuid']" --value-of 'text()' < $path)
    jo_args="$jo_args $(jo slug=$slug uuid=$uuid)"


    # --------- Code ends here
done < <(xmlstarlet sel -t --match "$xpath_sel" --value-of '@slug' --value-of "'$col_sep'" --value-of '@href' --value-of "'$col_sep'" --value-of '@style' --nl < $repo_root/META-INF/books.xml)

# Save all the slug/uuid pairs into a JSON file
# NOTE: This file is also used in convert-docx
jo -a $jo_args > "$book_slugs_file"

gdocify "$IO_JSONIFIED" "$IO_DOCX/content" "$book_slugs_file"
cp "$IO_DISASSEMBLE_LINKED"/*@*-metadata.json "$IO_DOCX/content"

lang="$(jq -r '.language' "$IO_JSONIFIED/"*.toc.json | uniq)"
# If there was more than one result from uniq, there were different languages
if [[ $(wc -l <<< "$lang") != 1 ]]; then
    die "Language mismatch between book slugs."  # LCOV_EXCL_LINE
fi


# Formerly git-convert-docx

# LCOV_EXCL_START
set -Eeuo pipefail

mathml2png_rpc start

book_slugs_file="$(realpath "$IO_DOCX/book-slugs.json")"
book_dir="$(realpath "$IO_DOCX/content")"
target_dir="$(realpath "$IO_DOCX/docx")"
pandoc_metadata_file="$(realpath "$IO_JSONIFIED/pandoc-metadata.json")"
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
        jq -r --arg language "$lang" '{ title: .title, language: $language, author: "OpenStax", company: "OpenStax" }' "$metadata_filename" > "$pandoc_metadata_file"
        docx_filename=$(jq -r '.slug' "$metadata_filename").docx
        mathmltable_tempfile="$xhtmlfile.mathmltable.tmp"
        mathmltable2png "$xhtmlfile" "../resources" "$mathmltable_tempfile"
        wrapped_tempfile="$xhtmlfile.greybox.tmp"

        say "Converting to docx: $xhtmlfile_basename"
        xsltproc --output "$wrapped_tempfile" "$BAKERY_SCRIPTS_ROOT/scripts/gdoc/wrap-in-greybox.xsl" "$mathmltable_tempfile"
        pandoc --fail-if-warnings --metadata-file="$pandoc_metadata_file" --reference-doc="$reference_doc" --from=html --to=docx --output="$current_target/$docx_filename" "$wrapped_tempfile"
    done
done < <(jq -r '.[] | .slug + "'$col_sep'" + .uuid' "$book_slugs_file")

mathml2png_rpc stop
# LCOV_EXCL_STOP
