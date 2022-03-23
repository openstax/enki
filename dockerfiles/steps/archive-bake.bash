parse_book_dir

try $COOKBOOK_ROOT/bake -b "$ARG_RECIPE_NAME" -i "$IO_ARCHIVE_BOOK/collection.linked.xhtml" -o "$IO_ARCHIVE_BOOK/collection.baked.xhtml"

style_file="$CNX_RECIPES_STYLES_ROOT/$ARG_RECIPE_NAME-pdf.css"

if [ -f "$style_file" ]; then
    cp "$style_file" "$IO_ARCHIVE_BOOK"
    try sed -i "s%<\\/head>%<link rel=\"stylesheet\" type=\"text/css\" href=\"$(basename $style_file)\" />&%" "$IO_ARCHIVE_BOOK/collection.baked.xhtml"
else
    yell "Warning: Could not find style file for recipe name '$ARG_RECIPE_NAME'" # LCOV_EXCL_LINE
fi
