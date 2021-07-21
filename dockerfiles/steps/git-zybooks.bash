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
for collection in "$IO_ASSEMBLED/"*.assembled.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
    if [[ -n "$ARG_OPT_ONLY_ONE_BOOK" ]]; then
        [[ "$slug_name" != "$ARG_OPT_ONLY_ONE_BOOK" ]] && continue # LCOV_EXCL_LINE
    fi
    try java -jar /usr/share/java/Saxon-HE.jar -xsl:$my_directory/git-zybooks.xslt -s:$IO_ASSEMBLED/$slug_name.assembled.xhtml -o:$IO_ZYBOOKS/$slug_name.assembled.xhtml
done
shopt -u globstar nullglob

