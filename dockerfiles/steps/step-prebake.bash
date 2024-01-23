# Formerly git-fetch-metadata
parse_book_dir

cp -R "$IO_FETCHED/." "$IO_FETCH_META"
neb pre-assemble "$IO_FETCH_META"
commit_sha="$(set +x && git -C "$IO_FETCH_META" log --format="%h" -1)"
rm -rf "$IO_FETCH_META/.git"

repo_info="$(set +x && neb parse-repo "$IO_FETCH_META")"
pages_root="$(set +x && echo "$repo_info" | jq -r '.container.pages_root')"
media_root="$(set +x && echo "$repo_info" | jq -r '.container.media_root')"

export HACK_CNX_LOOSENESS=1
# CNX user books do not always contain media directory
# Missing media files will still be caught by git-validate-references
if [[ -d "${media_root:?}" ]]; then
    fetch-map-resources "${pages_root:?}" "${media_root:?}" "$(dirname $IO_INITIAL_RESOURCES)" "$commit_sha"
    rm -rf "$media_root"
fi


# Copy web styles to the resources directory created by fetch-map-resources
style_resource_root="$IO_INITIAL_RESOURCES/styles"
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
        # LCOV_EXCL_START
        while read -r dependency; do
            expected_path="$style_resource_root/$dependency"
            if [[ ! -f "$expected_path" || ! "$(dirname "$expected_path")" =~ ^$IO_INITIAL_RESOURCES/[^/]+/.+$ ]]; then
                die "$expected_path, referenced in $style_src, does not exist or will not be uploaded." # LCOV_EXCL_LINE
            fi
        done < <(
            awk '$0 ~ /^.*url\(/ && $2 !~ /https?|data/ {
                # Get value of url()
                split($0, arr, /[()]/);
                dependency=arr[2]
                # Trim and remove double quotes
                gsub(/^ *|["]| *$/, "", dependency);
                print dependency;
            }' "$style_src"
        )
        # LCOV_EXCL_STOP
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
if [[ $LOCAL_ATTIC_DIR != '' ]]; then
    echo 'Annotating XML files with source map information (data-sm="...")'
    pushd $IO_FETCH_META > /dev/null
    files=$(find . -name '*.cnxml' -or -name '*.collection.xml')
    for file in $files; do
        node --unhandled-rejections=strict "${JS_EXTRA_VARS[@]}"  "$JS_UTILS_STUFF_ROOT/bin/bakery-helper" add-sourcemap-info "$file" "$file"
    done
    popd > /dev/null
fi

neb assemble "$repo_root" "$IO_ASSEMBLED"

# https://stackoverflow.com/a/31838754
xpath_sel="//*[@slug]" # All the book entries
while read -r slug; do # Loop over each <book> entry in the META-INF/books.xml manifest
    assembled_file="$IO_ASSEMBLED/$slug.assembled.xhtml"

    ## download exercise images and replace internet links with local resource links
    download-exercise-images "$IO_RESOURCES" "$assembled_file" "$assembled_file"
    
    # If there is any TeX math, replace it with mathml and highlight code that has data-lang ()
    if grep -E '.*data-(math|lang)=.+?' "$assembled_file" &> /dev/null; then
        mathified="$assembled_file.mathified.xhtml"
        node "${JS_EXTRA_VARS[@]}" $MATHIFY_ROOT/typeset/start.js -i "$assembled_file" -o "$mathified" -h 1 -f mathml
        mv "$mathified" "$assembled_file"
    fi
done < <(xmlstarlet sel -t --match "$xpath_sel" --value-of '@slug' --nl < "$repo_root/META-INF/books.xml")

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
