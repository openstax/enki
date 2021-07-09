# LCOV_EXCL_START
parse_book_dir
s3_bucket_prefix="apps/archive/${ARG_CODE_VERSION}"

book_metadata="${IO_ARCHIVE_FETCHED}/metadata.json"
resources_dir="${IO_ARCHIVE_BOOK}/resources"
target_dir="${IO_ARCHIVE_UPLOAD}/contents"
mkdir -p "$target_dir"
book_uuid="$(cat $book_metadata | jq -r '.id')"
book_version="$(cat $book_metadata | jq -r '.version')"

for jsonfile in "$IO_ARCHIVE_JSONIFIED/"*@*.json; do try cp "$jsonfile" "$target_dir/$(basename $jsonfile)"; done;
for xhtmlfile in "$IO_ARCHIVE_JSONIFIED/"*@*.xhtml; do try cp "$xhtmlfile" "$target_dir/$(basename $xhtmlfile)"; done;
try aws s3 cp --recursive "$target_dir" "s3://${ARG_S3_BUCKET_NAME}/${s3_bucket_prefix}/contents"
try copy-resources-s3 "$resources_dir" "${ARG_S3_BUCKET_NAME}" "${s3_bucket_prefix}/resources"

#######################################
# UPLOAD BOOK LEVEL FILES LAST
# so that if an error is encountered
# on prior upload steps, those files
# will not be found by watchers
#######################################
toc_s3_link_json="s3://${ARG_S3_BUCKET_NAME}/${s3_bucket_prefix}/contents/$book_uuid@$book_version.json"
toc_s3_link_xhtml="s3://${ARG_S3_BUCKET_NAME}/${s3_bucket_prefix}/contents/$book_uuid@$book_version.xhtml"
try aws s3 cp "$IO_ARCHIVE_JSONIFIED/collection.toc.json" "$toc_s3_link_json"
try aws s3 cp "$IO_ARCHIVE_JSONIFIED/collection.toc.xhtml" "$toc_s3_link_xhtml"

echo "DONE: See book at https://${ARG_S3_BUCKET_NAME}.s3.amazonaws.com/${s3_bucket_prefix}/contents/$book_uuid@$book_version.xhtml (maybe rename '-gatekeeper' to '-primary')"
# LCOV_EXCL_STOP
