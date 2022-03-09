#!/bin/bash
exec > >(tee "${COMMON_LOG_DIR}"/log >&2) 2>&1

reference=$(cat "${BOOK_INPUT}"/version)
[[ "$reference" = latest ]] && reference=main

creds_dir=tmp-gh-creds
creds_file="$creds_dir/gh-creds"
git config --global credential.helper "store --file=$creds_file"
mkdir "$creds_dir"
set +x
# Do not show creds
echo "https://$GH_SECRET_CREDS@github.com" > "$creds_file" 2>&1
set -x
remote="https://github.com/openstax/$(cat "${BOOK_INPUT}/repo").git"
GIT_TERMINAL_PROMPT=0 git clone --depth 1 "$remote" --branch "$reference" "${CONTENT_OUTPUT}/raw"
if [[ ! -f "${CONTENT_OUTPUT}/raw/collections/$(cat "${BOOK_INPUT}/slug").collection.xml" ]]; then
    echo "No matching book for slug in this repo"
    sleep 1
    exit 1
fi
fetch-update-meta "${CONTENT_OUTPUT}/raw/.git" "${CONTENT_OUTPUT}/raw/modules" "${CONTENT_OUTPUT}/raw/collections" "$reference" "${CONTENT_OUTPUT}/raw/canonical.json"
rm -rf "${CONTENT_OUTPUT}/raw/.git"
rm -rf "$creds_dir"

fetch-map-resources "${CONTENT_OUTPUT}/raw/modules" "${CONTENT_OUTPUT}/raw/media" . "${UNUSED_RESOURCE_OUTPUT}"
# Either the media is in resources or unused-resources, this folder should be empty (-d will fail otherwise)
rm -d "${CONTENT_OUTPUT}/raw/media"
