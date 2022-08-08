# This is mostly a copy/pasta of git-assemble.bash because 1. it was short and 2. is a good place to "fix" links to content not in this book.

# TODO: Make a giant module map and then redirect people from https://cnx.org/content/m1234 to the canonical book. Then these links will continue to work


repo_root=$IO_FETCH_META


# Tidy up the CNXML (by removing thumbnail attributes)
shopt -s globstar
for filename in **/*.cnxml; do # Whitespace-safe and recursive
    
    cat << EOF | try xsltproc --output "$filename" /dev/stdin "$filename"
        <xsl:stylesheet 
        xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
        xmlns:epub="http://www.idpf.org/2007/ops"
        xmlns:m="http://www.w3.org/1998/Math/MathML"
        xmlns:h="http://www.w3.org/1999/xhtml"
        xmlns:c="http://cnx.rice.edu/cnxml" 
        xmlns="http://www.w3.org/1999/xhtml"
        version="1.0">

        <!-- Discard image thumbnails -->
        <xsl:template match="c:image/@thumbnail" />

        <!-- Identity Transform -->
        <xsl:template match="@*|node()">
            <xsl:copy>
                <xsl:apply-templates select="@*|node()"/>
            </xsl:copy>
        </xsl:template>
        </xsl:stylesheet>
EOF

done
shopt -u globstar


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

    if [[ -f temp-assembly/collection.assembled.xhtml ]]; then
        rm temp-assembly/collection.assembled.xhtml
    fi

    export HACK_CNX_LOOSENESS=1 # Run neb assemble a bit looser. This deletes ToC items when the CNXML file is missing
    try neb assemble "$IO_FETCH_META/modules" temp-assembly/

    # fix_links_to_modules_outside_this_book
    cat << EOF | try xsltproc --output "$IO_ASSEMBLED/$slug.assembled.xhtml" /dev/stdin "temp-assembly/collection.assembled.xhtml"
<xsl:stylesheet 
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:epub="http://www.idpf.org/2007/ops"
  xmlns:m="http://www.w3.org/1998/Math/MathML"
  xmlns:h="http://www.w3.org/1999/xhtml"
  xmlns="http://www.w3.org/1999/xhtml"
  exclude-result-prefixes="h"
  version="1.0">

<!-- BUG in git-assemble. This fixes it for epubs but should be fixed for all books so that it is not done in the recipe -->
<xsl:template match="h:nav//h:a[contains(@href, '@.xhtml')]">
    <xsl:copy>
        <xsl:attribute name="href">
            <xsl:text>#page_</xsl:text>
            <xsl:value-of select="substring-before(@href, '@.xhtml')"/>
        </xsl:attribute>
    </xsl:copy>
</xsl:template>

<xsl:template match="h:nav//h:li">
    <xsl:copy>
        <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
</xsl:template>

<!-- Handle case when the CNXML link points to a collection instead of a module. The actual change _should_ be somewhere in neb assemble but I could not find it -->
<xsl:template match="h:a[starts-with(@href, &quot;/col&quot;) or starts-with(@href, &quot;/m&quot;)]/@href">
    <xsl:attribute name="href">
        <xsl:text>https://cnx.org/content/</xsl:text>
        <xsl:value-of select="substring-after(., &quot;/&quot;)"/>
    </xsl:attribute>
</xsl:template>

<xsl:template match="h:a[starts-with(@href, &quot;/contents/&quot;)]/@href">
    <xsl:attribute name="href">
        <xsl:text>https://cnx.org/content/</xsl:text>
        <xsl:value-of select="substring-after(., &quot;/contents/&quot;)"/>
    </xsl:attribute>
</xsl:template>

<xsl:template match="h:span/@width"/>

<xsl:template match="h:table/@summary"/>

<xsl:template match="@seperators">
    <xsl:attribute name="separators">
        <xsl:value-of select="."/>
    </xsl:attribute>
</xsl:template>

<!-- Identity Transform -->
<xsl:template match="@*|node()">
    <xsl:copy>
        <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
</xsl:template>
</xsl:stylesheet>
EOF

    try rm -rf temp-assembly
    try rm "$IO_FETCH_META/modules/collection.xml"



    # --------- Code ends here
done < <(try xmlstarlet sel -t --match "$xpath_sel" --value-of '@slug' --value-of "'$col_sep'" --value-of '@href' --value-of "'$col_sep'" --value-of '@style' --nl < $repo_root/META-INF/books.xml)
