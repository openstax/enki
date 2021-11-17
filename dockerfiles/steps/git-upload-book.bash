# LCOV_EXCL_START
parse_book_dir

s3_bucket_prefix="$PREVIEW_APP_URL_PREFIX/$CODE_VERSION"

# Parse the UUID and versions from the book metadata since it will be accessible
# for any pipeline (web-hosting or web-preview) and to be self-consistent
# metadata and values used.
book_metadata="$IO_JSONIFIED/$ARG_TARGET_SLUG_NAME.toc.json"
book_uuid=$(jq -r '.id' "$book_metadata")
book_version=$(jq -r '.version' "$book_metadata")
for jsonfile in "$IO_JSONIFIED/"*@*.json; do cp "$jsonfile" "$IO_ARTIFACTS/$(basename "$jsonfile")"; done;
for xhtmlfile in "$IO_JSONIFIED/"*@*.xhtml; do cp "$xhtmlfile" "$IO_ARTIFACTS/$(basename "$xhtmlfile")"; done;
try aws s3 cp --recursive "$IO_ARTIFACTS" "s3://$ARG_S3_BUCKET_NAME/$s3_bucket_prefix/contents"
try copy-resources-s3 "$IO_RESOURCES" "$ARG_S3_BUCKET_NAME" "$s3_bucket_prefix/resources"

# Copy subdirectories (Interactives)
for dirname in $(ls "$IO_RESOURCES"); do
    # Ensure dirname is a directory
    if [[ -d "$IO_RESOURCES/$dirname" ]]; then
        try aws s3 cp --recursive "$IO_RESOURCES/$dirname" "s3://$ARG_S3_BUCKET_NAME/$s3_bucket_prefix/resources/$dirname"
    fi
done

#######################################
# UPLOAD BOOK LEVEL FILES LAST
# so that if an error is encountered
# on prior upload steps, those files
# will not be found by watchers
#######################################
toc_s3_link_json="s3://$ARG_S3_BUCKET_NAME/$s3_bucket_prefix/contents/$book_uuid@$book_version.json"
toc_s3_link_xhtml="s3://$ARG_S3_BUCKET_NAME/$s3_bucket_prefix/contents/$book_uuid@$book_version.xhtml"
try aws s3 cp "$IO_JSONIFIED/$ARG_TARGET_SLUG_NAME.toc.json" "$toc_s3_link_json"
try aws s3 cp "$IO_JSONIFIED/$ARG_TARGET_SLUG_NAME.toc.xhtml" "$toc_s3_link_xhtml"

try cp "$IO_JSONIFIED/$ARG_TARGET_SLUG_NAME.toc.json" "$IO_ARTIFACTS/"
try cp "$IO_JSONIFIED/$ARG_TARGET_SLUG_NAME.toc.xhtml" "$IO_ARTIFACTS/"

echo "DONE: See book at https://$ARG_S3_BUCKET_NAME.s3.amazonaws.com/$s3_bucket_prefix/contents/$book_uuid@$book_version.xhtml (maybe rename '-gatekeeper' to '-primary')"
# LCOV_EXCL_STOP