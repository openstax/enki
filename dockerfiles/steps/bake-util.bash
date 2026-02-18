parse_book_dir

shopt -s globstar nullglob
cp -R "$BOOK_STYLES_ROOT/downloaded-fonts" "$IO_BAKED"
for collection in "$IO_ASSEMBLED/"*.assembled.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')

    style_name=$(read_style $slug_name)
    style_file="$BOOK_STYLES_ROOT/$style_name-pdf.css"
    dst_style_name="$slug_name-pdf.css"

    if [[ -f "$style_file" ]]; then
        cp "$style_file" "$IO_BAKED/$dst_style_name"
    else
        die "Warning: Style Not Found in '$style_file'" # LCOV_EXCL_LINE
    fi


    if [[ -f "$style_file" ]]; then
        # LCOV_EXCL_START
        if [[ -n "${SHORTEN:-}" ]]; then
            if
                ALLOW_UNKNOWN_ARGS=1 \
                "$COOKBOOK_ROOT/lib/recipes/$style_name/shorten" \
                    --input "$collection" \
                    --output "$collection.short" \
                    --keep-chapters "$SHORTEN"
            then
                mv "$collection" "$collection.orig"
                mv "$collection.short" "$collection"
                say "Shortened '$collection' ($SHORTEN)"
            fi
        fi
        # LCOV_EXCL_END
        export VERBOSE=$TRACE_ON
        $COOKBOOK_ROOT/bake -b "$style_name" -i "$IO_ASSEMBLED/$slug_name.assembled.xhtml" -o "$IO_BAKED/$slug_name.baked.xhtml" -r "$IO_RESOURCES" -p $1
        sed -i "s%<\\/head>%<link rel=\"stylesheet\" type=\"text/css\" href=\"$dst_style_name\" />&%" "$IO_BAKED/$slug_name.baked.xhtml"
    fi
done

baked_files=("$IO_BAKED"/*.baked.xhtml)
if [[ ${#baked_files[@]} -gt 0 ]]; then
    # Normalize git ref to a bare branch name or SHA for GitHub URLs.
    # Strips a leading remote prefix (e.g. origin/main -> main) but leaves
    # branch names with slashes (e.g. feature/my-branch) untouched.
    git_ref="$ARG_GIT_REF"
    [[ "$git_ref" == origin/* ]] && git_ref="${git_ref#origin/}"
    [[ "$git_ref" == upstream/* ]] && git_ref="${git_ref#upstream/}"
    node /workspace/enki/bakery-js/dist/index.js a11y \
        --repo "$ARG_REPO_NAME" --ref "$git_ref" --max-chapters 20 \
        "$IO_BAKED/a11y" "${baked_files[@]}"
fi

shopt -u globstar nullglob
