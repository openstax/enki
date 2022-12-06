parse_book_dir

set -Eeuxo pipefail


try node $JS_UTILS_STUFF_ROOT/bin/epub ./_attic/ $IO_EPUB/

# Generate the epub file
[[ -f $IO_ARTIFACTS/book.epub ]] && rm $IO_ARTIFACTS/book.epub
pushd $IO_EPUB/
zip $IO_ARTIFACTS/book.epub -DX0 mimetype
zip $IO_ARTIFACTS/book.epub -DX9 *
zip $IO_ARTIFACTS/book.epub -DX9 META-INF/container.xml
popd
