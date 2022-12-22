parse_book_dir

set -Eeuxo pipefail

# Ensure $IO_EPUB is empty
[[ -d $IO_EPUB ]] && rm -rf ${IO_EPUB:?}/*

try node --unhandled-rejections=strict $JS_UTILS_STUFF_ROOT/bin/bakery-helper epub ./ $IO_EPUB/

# Generate the epub files
[[ -f $IO_ARTIFACTS/*.epub ]] && rm $IO_ARTIFACTS/*.epub


shopt -s globstar nullglob
for book_dir in "$IO_EPUB/"*; do

    slug_name=$(basename $book_dir)
    pushd $book_dir
    zip $IO_ARTIFACTS/$slug_name.epub -DX0 mimetype
    zip $IO_ARTIFACTS/$slug_name.epub -DX9 META-INF/container.xml
    zip $IO_ARTIFACTS/$slug_name.epub -DX9 *
    popd

done
shopt -u globstar nullglob
