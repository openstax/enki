target_dir=$IO_ARCHIVE_BOOK
echo "{" > $IO_ARCHIVE_BOOK/uuid-to-revised-map.json
find $IO_ARCHIVE_FETCHED/ -path '*/m*/metadata.json' -print0 | xargs -0 cat | jq -r '. | "\"\(.id)\": \"\(.revised)\","' >> $IO_ARCHIVE_BOOK/uuid-to-revised-map.json
echo '"dummy": "dummy"' >> $IO_ARCHIVE_BOOK/uuid-to-revised-map.json
echo "}" >> $IO_ARCHIVE_BOOK/uuid-to-revised-map.json

assemble-meta "$IO_ARCHIVE_BOOK/collection.assembled.xhtml" $IO_ARCHIVE_BOOK/uuid-to-revised-map.json "$target_dir/collection.assembled-metadata.json"
rm $IO_ARCHIVE_BOOK/uuid-to-revised-map.json
