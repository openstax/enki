check_input_dir IO_RESOURCES

shopt -s globstar nullglob

for collection in "$IO_ASSEMBLED/"*.assembled.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
    if [[ -n "$ARG_OPT_ONLY_ONE_BOOK" ]]; then
        [[ "$slug_name" != "$ARG_OPT_ONLY_ONE_BOOK" ]] && continue # LCOV_EXCL_LINE
    fi

    set +e
    try xmlstarlet sel -t --match '//*[@src]' --value-of '@src' --nl < "$IO_ASSEMBLED/$slug_name.assembled.xhtml" > /tmp/references
    set -e

    while read reference_url; do
        if [[ $reference_url =~ ^https?:\/\/ ]]; then
            echo "skipping $reference_url"
            continue
        fi
        if [[ ! -f "$IO_ASSEMBLED/$reference_url" ]]; then
            echo $(realpath "$IO_ASSEMBLED/$reference_url")
            die "$reference_url invalid reference"
        else
            say "$reference_url valid reference"
        fi
    done < /tmp/references
done

shopt -u globstar nullglob
