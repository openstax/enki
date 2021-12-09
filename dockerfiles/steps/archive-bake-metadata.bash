parse_book_dir
book_metadata="$IO_ARCHIVE_FETCHED/metadata.json"
book_uuid="$(cat $book_metadata | jq -r '.id')"
book_version="$(cat $book_metadata | jq -r '.version')"
book_legacy_id="$(cat $book_metadata | jq -r '.legacy_id')"
book_legacy_version="$(cat $book_metadata | jq -r '.legacy_version')"
book_ident_hash="$book_uuid@$book_version"
book_license="$(cat $book_metadata | jq '.license')"
target_dir="$IO_ARCHIVE_BOOK"
book_slugs_file="/tmp/book-slugs.json"
cat "$IO_ARCHIVE_FETCHED/approved-book-list.json" | jq '[.approved_books[]|select(has("collection_id"))]|map(.books)|flatten' > "$book_slugs_file"
cat "$IO_ARCHIVE_BOOK/collection.assembled-metadata.json" | \
    jq --arg ident_hash "$book_ident_hash" --arg uuid "$book_uuid" --arg version "$book_version" --argjson license "$book_license" \
    --arg legacy_id "$book_legacy_id" --arg legacy_version "$book_legacy_version" \
    '. + {($ident_hash): {id: $uuid, version: $version, license: $license, legacy_id: $legacy_id, legacy_version: $legacy_version}}' > "/tmp/collection.baked-input-metadata.json"
try bake-meta /tmp/collection.baked-input-metadata.json "$target_dir/collection.baked.xhtml" "$book_uuid" "$book_slugs_file" "$target_dir/collection.baked-metadata.json"
