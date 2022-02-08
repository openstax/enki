parse_book_dir
# FIXME: Style devs will probably not like having to bake multiple books repeatedly,
# especially since they shouldn't care about link-extras correctness during their
# work cycle.

function read_style() {
    slug_name=$1
    if [[ ! -f $IO_BOOK/style ]]; then
        die "Style not specified. File does not exist '$IO_BOOK/style'" # LCOV_EXCL_LINE
    else
        style_name=$(cat $IO_BOOK/style)
        if [[ ! $style_name || $style_name == 'default' ]]; then
            style_name=$(xmlstarlet sel -t --match "//*[@style][@slug=\"$slug_name\"]" --value-of '@style' < $IO_FETCHED/META-INF/books.xml)
            if [[ $style_name == '' ]]; then
                die "Book style was not in the META-INF/books.xml file and was not specified (if this was built via CORGI)" # LCOV_EXCL_LINE
            fi
        fi
        echo $style_name
    fi
}

shopt -s globstar nullglob
for collection in "$IO_ASSEMBLED/"*.assembled.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')

    # use xmlstarlet to pull out the style file unless this ran in CORGI and the CORGI job has an override
    style_name=$(read_style $slug_name)
    style_file="$CNX_RECIPES_STYLES_ROOT/$style_name-pdf.css"

    if [[ -f "$style_file" ]]
        then
            try cp "$style_file" "$IO_BAKED/the-style-pdf.css"
        else
            die "Warning: Style Not Found in '$style_file'" # LCOV_EXCL_LINE
    fi


    if [[ -f "$style_file" ]]
        then
            export VERBOSE=$TRACE_ON
            try $RECIPES_ROOT/bake_root -b "$style_name" -r $CNX_RECIPES_RECIPES_ROOT/ -i "$IO_ASSEMBLED/$slug_name.assembled.xhtml" -o "$IO_BAKED/$slug_name.baked.xhtml"
            try sed -i "s%<\\/head>%<link rel=\"stylesheet\" type=\"text/css\" href=\"the-style-pdf.css\" />&%" "$IO_BAKED/$slug_name.baked.xhtml"
    fi
done
shopt -u globstar nullglob
