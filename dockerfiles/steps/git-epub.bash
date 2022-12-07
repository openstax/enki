parse_book_dir

set -Eeuxo pipefail

# Ensure $IO_EPUB is empty
[[ -d $IO_EPUB ]] && rm -rf $IO_EPUB/*

try node --unhandled-rejections=strict $JS_UTILS_STUFF_ROOT/bin/epub ./ $IO_EPUB/

# Generate the epub file
[[ -f $IO_ARTIFACTS/book.epub ]] && rm $IO_ARTIFACTS/book.epub
pushd $IO_EPUB/
zip $IO_ARTIFACTS/book.epub -DX0 mimetype
zip $IO_ARTIFACTS/book.epub -DX9 *
zip $IO_ARTIFACTS/book.epub -DX9 META-INF/container.xml
popd
