# Formerly git-fetch-metadata
parse_book_dir

[[ "$ARG_GIT_REF" == latest ]] && ARG_GIT_REF=main

cp -R "$IO_FETCHED/." "$IO_FETCH_META"

# Based on https://github.com/openstax/content-synchronizer/blob/e04c05fdce7e1bbba6a61a859b38982e17b74a16/resource-synchronizer/sync.sh#L19-L32
if [ ! -f $IO_FETCH_META/canonical.json ]; then
    slugs=()
    while IFS=$'\n' read -r line; do
        slugs+=("$line")
    done < <(xmlstarlet sel -t --match '//*[@slug]' --value-of '@slug' -n < "$IO_FETCH_META/META-INF/books.xml") # LCOV_EXCL_LINE
    if [[ ${#slugs[@]} == 0 ]]; then
        die "Could not find slugs in $IO_FETCH_META/META-INF/books.xml" # LCOV_EXCL_LINE
    fi
    jo -p -a "${slugs[@]}" > "$IO_FETCH_META/canonical.json"
fi

fetch-update-meta "$IO_FETCH_META/.git" "$IO_FETCH_META/modules" "$IO_FETCH_META/collections" "$ARG_GIT_REF" "$IO_FETCH_META/canonical.json"
rm -rf "$IO_FETCH_META/.git"

export HACK_CNX_LOOSENESS=1
# CNX user books do not always contain media directory
# Missing media files will still be caught by git-validate-references
if [[ -d "$IO_FETCH_META/media" ]]; then
    fetch-map-resources "$IO_FETCH_META/modules" "$IO_FETCH_META/media" "$(dirname $IO_INITIAL_RESOURCES)"
    rm -rf "${IO_FETCH_META:?}/media"
fi


# Copy web styles to the resources directory created by fetch-map-resources
style_resource_root="initial-resources/styles"
generic_style="webview-generic.css"
[[ ! -e "$style_resource_root" ]] && mkdir -p "$style_resource_root"
while read -r slug_name; do
    style_name=$(read_style "$slug_name")
    web_style="$style_name-web.css"
    if [[ ! -f "$BOOK_STYLES_ROOT/$web_style" ]]; then
        web_style="$generic_style"
    fi
    style_src="$BOOK_STYLES_ROOT/$web_style"
    style_dst="$style_resource_root/$web_style"
    if [[ ! -f "$style_dst" ]]; then
        # Check for resources that are not (1) online, or (2) encoded with data uri
        # Right now we assume no dependencies, but this may need to be revisited
        deps="$(awk '$0 ~ /^.*url\(/ && $2 !~ /http|data/ { print }' "$style_src")"
        if [[ $deps ]]; then
            die "Found unexpected dependencies in $style_src" # LCOV_EXCL_LINE
        fi
        cp "$style_src" "$style_dst"

        # Extract the sourcemap path from the file
        sourcemap_path="$(tail "$style_src" | awk '$0 ~ /\/\*# sourceMappingURL=/ { print substr($2, index($2, "=") + 1) }')"
        # Resolve the path to be absolute
        sourcemap_src="$(realpath "$BOOK_STYLES_ROOT/$sourcemap_path")"
        if [[ -f "$sourcemap_src" ]]; then
            # LCOV_EXCL_START
            # Find out if any directories need to be made before copying
            sourcemap_name="$(basename "$sourcemap_src")"
            sourcemap_dir_rel="$(realpath "$(dirname "$sourcemap_src")" --relative-to "$BOOK_STYLES_ROOT")"
            sourcemap_dst="$style_resource_root/$sourcemap_dir_rel/$sourcemap_name"
            # If the realtive path starts with '..', it is not in a subdirectory
            if [[ "$sourcemap_dir_rel" =~ ^\.\..+$ ]]; then
                die "Style sourcemap must be within $BOOK_STYLES_ROOT or one of its subdirectories" # LCOV_EXCL_LINE
            fi
            parent_path="$(dirname "$sourcemap_dst")"
            [[ ! -e  "$parent_path" ]] && mkdir -p "$parent_path"
            cp "$sourcemap_src" "$sourcemap_dst"
            # LCOV_EXCL_STOP
        fi
    fi
done < <(xmlstarlet sel -t -m '//*[@slug]' -v '@slug' -n < "$IO_FETCH_META/META-INF/books.xml")


# Formerly git-assemble
parse_book_dir

cp -r "$IO_INITIAL_RESOURCES/." "$IO_RESOURCES"

repo_root=$IO_FETCH_META

# TODO: Pass file name pattern to node command and avoid the loop below
if [[ $LOCAL_ATTIC_DIR != '' && -z $SKIP_SOURCE_INFO ]]; then
    echo 'Annotating XML files with source map information (data-sm="...")'
    pushd $IO_FETCH_META > /dev/null
    files=$(find . -name '*.cnxml' -or -name '*.collection.xml')
    for file in $files; do
        node --unhandled-rejections=strict "${JS_EXTRA_VARS[@]}"  "$JS_UTILS_STUFF_ROOT/bin/bakery-helper" add-sourcemap-info "$file" "$file"
    done
    popd > /dev/null
fi

col_sep='|'
# https://stackoverflow.com/a/31838754
xpath_sel="//*[@slug]" # All the book entries
while read -r line; do # Loop over each <book> entry in the META-INF/books.xml manifest
    IFS=$col_sep read -r slug href _ <<< "$line"
    path="$repo_root/META-INF/$href"
    assembled_file="$IO_ASSEMBLED/$slug.assembled.xhtml"

    # ------------------------------------------
    # Available Variables: slug href style path
    # ------------------------------------------
    # --------- Code starts here



    cp "$path" "$IO_FETCH_META/modules/collection.xml"

    if [[ -f temp-assembly/collection.assembled.xhtml ]]; then
        rm temp-assembly/collection.assembled.xhtml # LCOV_EXCL_LINE
    fi

    neb assemble "$IO_FETCH_META/modules" temp-assembly/

    ## download exercise images and replace internet links with local resource links
    download-exercise-images "$IO_RESOURCES" "temp-assembly/collection.assembled.xhtml" "$assembled_file"
    
    if grep -E '.*data-math=.+?' "$assembled_file" &> /dev/null; then
        mathified="$assembled_file.mathified.xhtml"
        node "${JS_EXTRA_VARS[@]}" $MATHIFY_ROOT/typeset/start.js -i "$assembled_file" -o "$mathified" -f mathml
        mv "$mathified" "$assembled_file"
    fi

    rm -rf temp-assembly
    rm "$IO_FETCH_META/modules/collection.xml"



    # --------- Code ends here
done < <(xmlstarlet sel -t --match "$xpath_sel" --value-of '@slug' --value-of "'$col_sep'" --value-of '@href' --value-of "'$col_sep'" --value-of '@style' --nl < $repo_root/META-INF/books.xml)

# Formerly git-validate-references
check_input_dir IO_RESOURCES

shopt -s globstar nullglob

for collection in "$IO_ASSEMBLED/"*.assembled.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')

    if [[ ! -f "$IO_ASSEMBLED/$slug_name.assembled.xhtml" ]]; then
        die "Expected $IO_ASSEMBLED/$slug_name.assembled.xhtml to exist" # LCOV_EXCL_LINE
    fi

    set +e
    xmlstarlet sel -t --match '//*[@src]' --value-of '@src' --nl < "$IO_ASSEMBLED/$slug_name.assembled.xhtml" > /tmp/references
    set -e

    while read reference_url; do
        if [[ $reference_url =~ ^https?:\/\/ ]]; then
            echo "skipping $reference_url"
            continue
        fi
        if [[ ! -f "$IO_ASSEMBLED/$reference_url" ]]; then
            # LCOV_EXCL_START
            abs_path=$(realpath "$IO_ASSEMBLED/$reference_url")
            die "$reference_url invalid reference. A file does not exist at this location '$abs_path'"
            # LCOV_EXCL_STOP
        fi
    done < /tmp/references # LCOV_EXCL_LINE
done

shopt -u globstar nullglob

# Formerly git-assemble-meta
shopt -s globstar nullglob
# Create an empty map file for invoking assemble-meta
echo "{}" > uuid-to-revised-map.json
for collection in "$IO_ASSEMBLED/"*.assembled.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
    assemble-meta "$IO_ASSEMBLED/$slug_name.assembled.xhtml" uuid-to-revised-map.json "$IO_ASSEMBLE_META/$slug_name.assembled-metadata.json"
done
rm uuid-to-revised-map.json
shopt -u globstar nullglob
