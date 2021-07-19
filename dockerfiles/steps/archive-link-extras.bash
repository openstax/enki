book_server=archive.cnx.org
# https://github.com/openstax/output-producer-service/blob/master/bakery/src/tasks/link-extras.js#L40
try python3 $BAKERY_SCRIPTS_ROOT/scripts/link_extras.py "$IO_ARCHIVE_BOOK" "$book_server" $BAKERY_SCRIPTS_ROOT/scripts/canonical-book-list.json
