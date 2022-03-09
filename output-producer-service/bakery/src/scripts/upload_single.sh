#!/bin/bash
exec > >(tee "${COMMON_LOG_DIR}"/log >&2) 2>&1

target_dir="${UPLOAD_OUTPUT}/contents"
mkdir -p "$target_dir"
book_dir="${JSONIFIED_INPUT}"
book_slug=$(cat "${BOOK_INPUT}"/slug)
# Parse the UUID and versions from the book metadata since it will be accessible
# for any pipeline (web-hosting or web-preview) and to be self-consistent
# metadata and values used.
book_metadata="${JSONIFIED_INPUT}/$book_slug.toc.json"
book_uuid=$(jq -r '.id' "$book_metadata")
book_version=$(jq -r '.version' "$book_metadata")
for jsonfile in "$book_dir/"*@*.json; do cp "$jsonfile" "$target_dir/$(basename "$jsonfile")"; done;
for xhtmlfile in "$book_dir/"*@*.xhtml; do cp "$xhtmlfile" "$target_dir/$(basename "$xhtmlfile")"; done;
aws s3 cp --recursive "$target_dir" "s3://${BUCKET}/${BUCKET_PREFIX}/contents"
copy-resources-s3 "${RESOURCE_INPUT}" "${BUCKET}" "${BUCKET_PREFIX}/resources"

#######################################
# UPLOAD BOOK LEVEL FILES LAST
# so that if an error is encountered
# on prior upload steps, those files
# will not be found by watchers
#######################################
toc_s3_link_json="s3://${BUCKET}/${BUCKET_PREFIX}/contents/$book_uuid@$book_version.json"
toc_s3_link_xhtml="s3://${BUCKET}/${BUCKET_PREFIX}/contents/$book_uuid@$book_version.xhtml"
aws s3 cp "$book_dir/$book_slug.toc.json" "$toc_s3_link_json"
aws s3 cp "$book_dir/$book_slug.toc.xhtml" "$toc_s3_link_xhtml"
