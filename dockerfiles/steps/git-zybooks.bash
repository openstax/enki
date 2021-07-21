# Parse the assembled file, write XML files out using XSLT
# convert XML files to JSON (maybe also using SAXON-HE)
# Run pygmentize (docbook did it: https://xsltng.docbook.org/guide/ext_pygmentize.html)
# Documentation: https://docs.google.com/document/d/1MY8mQGfAhhYYzIX3DEIDW-rgNs7AZw7w-utu_Rp6n8Q/edit

# Use this test book: https://github.com/philschatz/tiny-book/tree/zybooks
# Use this command:
#
# ./cli.sh data/tin-bk/ all-git-pdf philschatz/tiny-book/book-slug1 chemistry zybooks

my_directory=/dockerfiles/steps

shopt -s globstar nullglob
for collection in "$IO_PRE_ZYBOOKS/"*.assembled.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
    if [[ -n "$ARG_OPT_ONLY_ONE_BOOK" ]]; then
        [[ "$slug_name" != "$ARG_OPT_ONLY_ONE_BOOK" ]] && continue # LCOV_EXCL_LINE
    fi
    try java -jar /usr/share/java/Saxon-HE.jar -xsl:$my_directory/git-zybooks.xslt -s:$IO_PRE_ZYBOOKS/$slug_name.assembled.xhtml -o:$IO_ASSEMBLED/$slug_name.assembled.xhtml CODE_VERSION=$CODE_VERSION

    for filename_src_value in $(xmlstarlet 'select' --text --template --value-of '//@src' $IO_ASSEMBLED/$slug_name.assembled.xhtml); do
        # TODO Do not assume the file is in the same director. Make it work with relative paths
        old_filepath=$IO_ASSEMBLED/$filename_src_value
        [[ -f $old_filepath ]] || die "Could not find file $old_filepath"

        new_filename=$(sha256sum $old_filepath | awk '{print $1}')

        try mv $old_filepath $IO_ASSEMBLED/../resources/$new_filename

        # Move each JSON file into the resources directory and update the XHTML file
        xmlstarlet edit --inplace --update "//*[@src='$filename_src_value']/@src" --value "../resources/$new_filename" $IO_ASSEMBLED/$slug_name.assembled.xhtml
    
    done
done
shopt -u globstar nullglob

