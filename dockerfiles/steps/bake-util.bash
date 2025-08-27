parse_book_dir

shopt -s globstar nullglob
cp -R "$BOOK_STYLES_ROOT/downloaded-fonts" "$IO_BAKED"
for collection in "$IO_ASSEMBLED/"*.assembled.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')

    style_name=$(read_style $slug_name)
    style_file="$BOOK_STYLES_ROOT/$style_name-pdf.css"
    dst_style_name="$slug_name-pdf.css"

    if [[ -f "$style_file" ]]
        then
            cp "$style_file" "$IO_BAKED/$dst_style_name"
        else
            die "Warning: Style Not Found in '$style_file'" # LCOV_EXCL_LINE
    fi


    if [[ -f "$style_file" ]]
        then
            export VERBOSE=$TRACE_ON
            $COOKBOOK_ROOT/bake -b "$style_name" -i "$IO_ASSEMBLED/$slug_name.assembled.xhtml" -o "$IO_BAKED/$slug_name.baked.xhtml" -r "$IO_RESOURCES" -p $1
            sed -i "s%<\\/head>%<link rel=\"stylesheet\" type=\"text/css\" href=\"$dst_style_name\" />&%" "$IO_BAKED/$slug_name.baked.xhtml"
    fi
done
shopt -u globstar nullglob
