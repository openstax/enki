repo_root=$IO_FETCH_META
col_sep='|'
# https://stackoverflow.com/a/31838754
xpath_sel="//*[@slug]" # All the book entries
if [[ $ARG_TARGET_SLUG_NAME ]]; then
    xpath_sel="//*[@slug=\"$ARG_TARGET_SLUG_NAME\"]" # LCOV_EXCL_LINE
fi
while read -r line; do # Loop over each <book> entry in the META-INF/books.xml manifest
    IFS=$col_sep read -r slug href _ <<< "$line"
    path="$repo_root/META-INF/$href"

    # ------------------------------------------
    # Available Variables: slug href style path
    # ------------------------------------------
    # --------- Code starts here



    try cp "$path" "$IO_FETCH_META/modules/collection.xml"

    try neb assemble "$IO_FETCH_META/modules" temp-assembly/

    try cp "temp-assembly/collection.assembled.xhtml" "$IO_ASSEMBLED/$slug.assembled.xhtml"
    remove_metadata=$(cat << EOF
<xsl:stylesheet 
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns="http://www.w3.org/1999/xhtml"
  version="1.0">

<xsl:template match="*[@data-type='page']/*[@data-type='metadata']" />

<!-- Identity Transform -->
<xsl:template match="@*|node()">
    <xsl:copy>
        <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
</xsl:template>
</xsl:stylesheet>
EOF)
    echo $remove_metadata | try xsltproc --output "$IO_ASSEMBLED/$slug.assembled.xhtml" /dev/stdin "temp-assembly/collection.assembled.xhtml"

    try rm -rf temp-assembly
    try rm "$IO_FETCH_META/modules/collection.xml"



    # --------- Code ends here
done < <(try xmlstarlet sel -t --match "$xpath_sel" --value-of '@slug' --value-of "'$col_sep'" --value-of '@href' --value-of "'$col_sep'" --value-of '@style' --nl < $repo_root/META-INF/books.xml)
