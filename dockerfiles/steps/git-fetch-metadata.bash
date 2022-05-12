try cp -R "$IO_FETCHED/." "$IO_FETCH_META"

# Based on https://github.com/openstax/content-synchronizer/blob/e04c05fdce7e1bbba6a61a859b38982e17b74a16/resource-synchronizer/sync.sh#L19-L32
if [ ! -f $IO_FETCH_META/canonical.json ]; then
    slugs=()
    while IFS=$'\n' read -r line; do
        slugs+=("$line")
    done < <(try xmlstarlet sel -t --match '//*[@slug]' --value-of '@slug' -n < "$IO_FETCH_META/META-INF/books.xml") # LCOV_EXCL_LINE
    if [[ ${#slugs[@]} == 0 ]]; then
        die "Could not find slugs in $IO_FETCH_META/META-INF/books.xml" # LCOV_EXCL_LINE
    fi
    jo -p -a "${slugs[@]}" > "$IO_FETCH_META/canonical.json"
fi

try fetch-update-meta "$IO_FETCH_META/.git" "$IO_FETCH_META/modules" "$IO_FETCH_META/collections" "$ARG_GIT_REF" "$IO_FETCH_META/canonical.json"
try rm -rf "$IO_FETCH_META/.git"

try fetch-map-resources "$IO_FETCH_META/modules" "$IO_FETCH_META/media" . "$IO_UNUSED_RESOURCES"
# Either the media is in resources or unused-resources, this folder should be empty (-d will fail otherwise)
try rm -d "$IO_FETCH_META/media"

# Copy web styles to the resources directory created by fetch-map-resources
style_resource_root="resources/styles"
generic_style="webview-generic.css"
[[ ! -e "$style_resource_root" ]] && mkdir -p "$style_resource_root"
while read -r slug_name; do
    style_name=$(read_style "$slug_name")
    web_style="$style_name-web.css"
    if [[ ! -f "$CNX_RECIPES_STYLES_ROOT/$web_style" ]]; then
        web_style="$generic_style"
    fi
    style_src="$CNX_RECIPES_STYLES_ROOT/$web_style"
    style_dst="$style_resource_root/$web_style"
    if [[ ! -f "$style_dst" ]]; then
        # Check for resources that are not (1) online, or (2) encoded with data uri
        # Right now we assume no dependencies, but this may need to be revisited
        deps="$(try awk '$0 ~ /^.*url\(/ && $2 !~ /http|data/ { print }' "$style_src")"
        if [[ $deps ]]; then
            die "Found unexpected dependencies in $style_src" # LCOV_EXCL_LINE
        fi
        try cp "$style_src" "$style_dst"

        sourcemap_name="$(tail "$style_src" | awk '$1 ~ /\/\*#/ { print $2 }' | awk -F '=' '{ print $2 }')"
        sourcemap_src="$CNX_RECIPES_STYLES_ROOT/$sourcemap_name"
        sourcemap_dst="$style_resource_root/$sourcemap_name"
        if [[ -f "$sourcemap_src" ]]; then
            # LCOV_EXCL_START
            if [[ "$(dirname "$sourcemap_src")" != "$(dirname "$style_src")" ]]; then
                die "Style sourcemap must be in the same directory as style file"
            fi
            try cp "$sourcemap_src" "$sourcemap_dst"
            # LCOV_EXCL_STOP
        fi
    fi
done < <(try xmlstarlet sel -t -m '//*[@slug]' -v '@slug' -n < "$IO_FETCH_META/META-INF/books.xml")
