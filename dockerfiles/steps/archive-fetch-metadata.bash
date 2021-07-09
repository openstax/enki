book_slugs_url='https://raw.githubusercontent.com/openstax/content-manager-approved-books/master/approved-book-list.json'
try wget "${book_slugs_url}" -O "${IO_ARCHIVE_FETCHED}/approved-book-list.json"
