parse_book_dir
# FIXME: We assume that every book in the group uses the same style
# This assumption will not hold true forever, and book style + recipe name should
# be pulled from fetched-book-group (while still allowing injection w/ CLI)

# FIXME: Style devs will probably not like having to bake multiple books repeatedly,
# especially since they shouldn't care about link-extras correctness during their
# work cycle.

shopt -s globstar nullglob
for collection in "$IO_ASSEMBLED/"*.assembled.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
    if [[ -n "$ARG_OPT_ONLY_ONE_BOOK" ]]; then
        [[ "$slug_name" != "$ARG_OPT_ONLY_ONE_BOOK" ]] && continue # LCOV_EXCL_LINE
    fi

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
    try $RECIPES_ROOT/bake_root -b "$style_name" -r $CNX_RECIPES_RECIPES_ROOT/ -i "$IO_ASSEMBLED/$slug_name.assembled.xhtml" -o "$IO_BAKED/$slug_name.baked.xhtml"
        then
            try sed -i "s%<\\/head>%<link rel=\"stylesheet\" type=\"text/css\" href=\"the-style-pdf.css\" />&%" "$IO_BAKED/$slug_name.baked.xhtml"
    fi
done
shopt -u globstar nullglob
