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
        else
            say "$reference_url valid reference"
        fi
    done < /tmp/references # LCOV_EXCL_LINE
done

shopt -u globstar nullglob
