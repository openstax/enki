try cp -R "$IO_FETCHED/." "$IO_FETCH_META"

# From https://github.com/openstax/content-synchronizer/blob/e04c05fdce7e1bbba6a61a859b38982e17b74a16/resource-synchronizer/sync.sh#L19-L32
if [ ! -f $IO_FETCH_META/canonical.json ]; then
    # Create a temporary ./archive-syncfile
    try xmlstarlet sel -t --match '//*[@slug]' --value-of '@slug' --value-of '" "' --value-of '@collection-id' --nl < $IO_FETCH_META/META-INF/books.xml > $IO_FETCH_META/archive-syncfile

    # Write the $IO_FETCH_META/canonical.json file out
    [[ ! -f $IO_FETCH_META/canonical-temp.txt ]] || try rm $IO_FETCH_META/canonical-temp.txt
    try echo '[' > $IO_FETCH_META/canonical.json
    while read slug; do
        try echo "    \"$slug\"" >> $IO_FETCH_META/canonical-temp.txt
    done < $IO_FETCH_META/archive-syncfile # LCOV_EXCL_LINE
    # Add a comma to every line except the last line https://stackoverflow.com/a/35021663
    try sed '$!s/$/,/' $IO_FETCH_META/canonical-temp.txt >> $IO_FETCH_META/canonical.json
    try rm $IO_FETCH_META/canonical-temp.txt
    try echo ']' >> $IO_FETCH_META/canonical.json
    try rm $IO_FETCH_META/archive-syncfile
fi

try fetch-update-meta "$IO_FETCH_META/.git" "$IO_FETCH_META/modules" "$IO_FETCH_META/collections" "$ARG_GIT_REF" "$IO_FETCH_META/canonical.json"
try rm -rf "$IO_FETCH_META/.git"

try fetch-map-resources "$IO_FETCH_META/modules" "$IO_FETCH_META/media" . "$IO_UNUSED_RESOURCES"
# Either the media is in resources or unused-resources, this folder should be empty (-d will fail otherwise)
try rm -d "$IO_FETCH_META/media"

# Copy web styles to the resources directory created by fetch-map-resources
style_resource_root="resources/styles"
[[ ! -e "$style_resource_root" ]] && mkdir -p "$style_resource_root"
while read -r slug_name; do
    style_name=$(read_style "$slug_name")
    web_style="$style_name-rex-web.css"
    style_src="$CNX_RECIPES_STYLES_ROOT/$web_style"
    style_dst="$style_resource_root/$style_name-web.css"
    if [[ -f "$style_src" && ! -f "$style_dst" ]]; then
        # Check for resources that are not (1) online, or (2) encoded with data uri
        # Right now we assume no dependencies, but this may need to be revisited
        deps="$(awk '$0 ~ /^.*url\(/ && $2 !~ /http|data/ { print }' "$style_src")"
        if [[ $deps ]]; then
            die "Found unexpected dependencies in $style_src" # LCOV_EXCL_LINE
        fi
        try cp "$style_src" "$style_dst"
    fi
done < <(try xmlstarlet sel -t -m '//*[@slug]' -v '@slug' -n < "$IO_FETCH_META/META-INF/books.xml")
