parse_book_dir

s3_bucket_prefix="$PREVIEW_APP_URL_PREFIX/$CODE_VERSION"

for jsonfile in "$IO_JSONIFIED/"*@*:*.json; do cp "$jsonfile" "$IO_ARTIFACTS/$(basename "$jsonfile")"; done;
for xhtmlfile in "$IO_JSONIFIED/"*@*:*.xhtml; do cp "$xhtmlfile" "$IO_ARTIFACTS/$(basename "$xhtmlfile")"; done;
aws s3 cp --recursive "$IO_ARTIFACTS" "s3://$ARG_S3_BUCKET_NAME/$s3_bucket_prefix/contents"
copy-resources-s3 "$IO_RESOURCES" "$ARG_S3_BUCKET_NAME" "$s3_bucket_prefix/resources"

# Copy subdirectories (Interactives and styles)
shopt -s globstar nullglob
for subdir in "$IO_RESOURCES"/*/; do
    dirname=$(basename $subdir)
    aws s3 cp --recursive "$subdir" "s3://$ARG_S3_BUCKET_NAME/$s3_bucket_prefix/resources/$dirname"
done
shopt -u globstar nullglob


shopt -s globstar nullglob
for collection in "$IO_JSONIFIED/"*.toc.json; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')


    # Parse the UUID and versions from the book metadata since it will be accessible
    # for any pipeline (web-hosting or web-preview) and to be self-consistent
    # metadata and values used.
    book_metadata="$IO_JSONIFIED/$slug_name.toc.json"
    book_uuid=$(jq -r '.id' "$book_metadata")
    book_version=$(jq -r '.version' "$book_metadata")

    #######################################
    # UPLOAD BOOK LEVEL FILES LAST
    # so that if an error is encountered
    # on prior upload steps, those files
    # will not be found by watchers
    #######################################
    toc_s3_link_json="s3://$ARG_S3_BUCKET_NAME/$s3_bucket_prefix/contents/$book_uuid@$book_version.json"
    toc_s3_link_xhtml="s3://$ARG_S3_BUCKET_NAME/$s3_bucket_prefix/contents/$book_uuid@$book_version.xhtml"
    aws s3 cp "$IO_JSONIFIED/$slug_name.toc.json" "$toc_s3_link_json"
    aws s3 cp "$IO_JSONIFIED/$slug_name.toc.xhtml" "$toc_s3_link_xhtml"

    cp "$IO_JSONIFIED/$slug_name.toc.json" "$IO_ARTIFACTS/"
    cp "$IO_JSONIFIED/$slug_name.toc.xhtml" "$IO_ARTIFACTS/"

    echo "DONE: See book at https://$ARG_S3_BUCKET_NAME.s3.amazonaws.com/$s3_bucket_prefix/contents/$book_uuid@$book_version.xhtml (maybe rename '-gatekeeper' to '-primary')"


done

# Only do this when we are running a CORGI job
if $ARG_ENABLE_CORGI_UPLOAD; then
    for varname in CORGI_CLOUDFRONT_URL REX_PROD_PREVIEW_URL; do
        : ${!varname:?"Expected value for \"$varname\""}
    done
    book_slug_urls=()
    while read -r book_slug; do
        book_metadata="$IO_ARTIFACTS/$book_slug.toc.json"

        book_uuid=$(jq -r '.id' "$book_metadata")
        book_version=$(jq -r '.version' "$book_metadata")

        rex_archive_param="?archive=$CORGI_CLOUDFRONT_URL/$PREVIEW_APP_URL_PREFIX/$CODE_VERSION"

        first_page_slug=$(jq -r '.tree.contents[0].slug' "$book_metadata")
        rex_prod_url="$REX_PROD_PREVIEW_URL/apps/rex/books/$book_uuid@$book_version/pages/$first_page_slug$rex_archive_param"

        book_slug_urls+=("$(jo url="$rex_prod_url" slug="$book_slug")")
    done < <(read_book_slugs)  # LCOV_EXCL_LINE

    jo -a "${book_slug_urls[@]}" > "$IO_ARTIFACTS/artifact_urls.json"

    echo "View web preview here: $rex_prod_url"
fi

shopt -u globstar nullglob
