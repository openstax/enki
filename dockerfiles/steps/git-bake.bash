parse_book_dir

shopt -s globstar nullglob
for collection in "$IO_ASSEMBLED/"*.assembled.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')

    # use xmlstarlet to pull out the style file unless this ran in CORGI and the CORGI job has an override
    style_name=$(read_style $slug_name)
    style_file="$BOOK_STYLES_ROOT/$style_name-pdf.css"

    if [[ -f "$style_file" ]]
        then
            try cp "$style_file" "$IO_BAKED/the-style-pdf.css"
        else
            die "Warning: Style Not Found in '$style_file'" # LCOV_EXCL_LINE
    fi


    if [[ -f "$style_file" ]]
        then
            export VERBOSE=$TRACE_ON
            try $COOKBOOK_ROOT/bake -b "$style_name" -i "$IO_ASSEMBLED/$slug_name.assembled.xhtml" -o "$IO_BAKED/$slug_name.baked.xhtml"
            try sed -i "s%<\\/head>%<link rel=\"stylesheet\" type=\"text/css\" href=\"the-style-pdf.css\" />&%" "$IO_BAKED/$slug_name.baked.xhtml"
    fi
done
shopt -u globstar nullglob
