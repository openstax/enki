# This is mostly a copy/pasta of git-assemble.bash because 1. it was short and 2. is a good place to "fix" links to content not in this book.

# TODO: Make a giant module map and then redirect people from https://cnx.org/content/m1234 to the canonical book. Then these links will continue to work

parse_book_dir

repo_root=$IO_FETCH_META



# Tidy up the CNXML (by removing thumbnail attributes)
shopt -s globstar
for filename in **/*.cnxml; do # Whitespace-safe and recursive
    
    cat << EOF | try xsltproc --output "$filename" --stringparam moduleid "$(basename "$(dirname "$filename")")" /dev/stdin "$filename"
        <xsl:stylesheet 
        xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
        xmlns:epub="http://www.idpf.org/2007/ops"
        xmlns:m="http://www.w3.org/1998/Math/MathML"
        xmlns:h="http://www.w3.org/1999/xhtml"
        xmlns:c="http://cnx.rice.edu/cnxml"
        xmlns:str="http://exslt.org/strings"
        xmlns="http://www.w3.org/1999/xhtml"
        version="1.0">
        
        <xsl:param name="moduleid"/>

        <!-- Discard image thumbnails -->
        <xsl:template match="c:image/@thumbnail" />

        <xsl:template match="c:code/c:caption">
            <c:span>
                <xsl:apply-templates select="@*|node()"/>
            </c:span>
        </xsl:template>

        <!-- Make resource links go to the module on cnx.org -->
        <xsl:template match="c:download[@src][not(starts-with(@src, 'http') or starts-with(@src, '/') or starts-with(@src, '#'))]/@src|
                             c:link[@url][not(starts-with(@url, 'http') or starts-with(@url, '/') or starts-with(@src, '#'))]/@url">
            <xsl:attribute name="{name()}">
                <xsl:text>https://cnx.org/content/</xsl:text>
                <xsl:value-of select="\$moduleid"/>
                <xsl:text>/</xsl:text>
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
        rm temp-assembly/collection.assembled.xhtml # LCOV_EXCL_LINE
    fi

    export HACK_CNX_LOOSENESS=1 # Run neb assemble a bit looser. This deletes ToC items when the CNXML file is missing
    try neb assemble "$IO_FETCH_META/modules" temp-assembly/

    # fix_links_to_modules_outside_this_book
    cat << EOF | try xsltproc --output "$IO_ASSEMBLED/$slug.assembled.xhtml" /dev/stdin "temp-assembly/collection.assembled.xhtml"
<xsl:stylesheet 
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:epub="http://www.idpf.org/2007/ops"
  xmlns:m="http://www.w3.org/1998/Math/MathML"
  xmlns:c="http://cnx.rice.edu/cnxml"
  xmlns:h="http://www.w3.org/1999/xhtml"
  xmlns="http://www.w3.org/1999/xhtml"
  exclude-result-prefixes="h epub"
  version="1.0">

<!-- BUG in git-assemble. This fixes it for epubs but should be fixed for all books so that it is not done in the recipe -->
<xsl:template match="h:nav//h:a[contains(@href, '@.xhtml')]">
    <xsl:variable name="the_id">
        <xsl:text>page_</xsl:text>
        <xsl:value-of select="substring-before(@href, '@.xhtml')"/>
    </xsl:variable>

    <xsl:copy>
        <xsl:attribute name="href">
            <xsl:text>#</xsl:text>
            <xsl:value-of select="\$the_id"/>
        </xsl:attribute>
        
        <xsl:apply-templates select="node()"/>
    </xsl:copy>
</xsl:template>

<xsl:template match="h:nav//h:li">
    <xsl:copy>
        <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
</xsl:template>

<!-- _window is no longer a valid target. _blank is nearest -->
<xsl:template match="h:a[@target = '_window']/@target">
    <xsl:attribute name="target">
        <xsl:text>_blank</xsl:text>
    </xsl:attribute>
</xsl:template>

<!-- Remove empty display attributes -->
<xsl:template match="m:*[@display = '']/@display"/>

<!-- Handle case when the CNXML link points to a collection instead of a module. The actual change _should_ be somewhere in neb assemble but I could not find it -->
<xsl:template match="h:a[starts-with(@href, &quot;/col&quot;) or starts-with(@href, &quot;/m&quot;)]/@href">
    <xsl:attribute name="href">
        <xsl:text>https://cnx.org/content/</xsl:text>
        <xsl:value-of select="substring-after(., &quot;/&quot;)"/>
    </xsl:attribute>
</xsl:template>

<!-- Convert divs with display="inline" into spans -->
<xsl:template match="h:div[@display = 'inline']">
    <span>
        <xsl:apply-templates select="@*[not(name() = 'display')]|node()"/>
    </span>
</xsl:template>

<!-- Convert iframes to links -->
<xsl:template match="h:iframe">
    <a>
        <xsl:attribute name="href">
            <xsl:value-of select="@src"/>
        </xsl:attribute>
        <xsl:value-of select="@src"/>
    </a>
</xsl:template>

<xsl:template match="h:a[starts-with(@href, &quot;/contents/&quot;)]/@href">
    <xsl:attribute name="href">
        <xsl:text>https://cnx.org/content/</xsl:text>
        <xsl:value-of select="substring-after(., &quot;/contents/&quot;)"/>
    </xsl:attribute>
</xsl:template>

<xsl:template match="h:span/@width"/>

<xsl:template match="h:table/@summary"/>

<!-- q is inline display by default -->
<xsl:template match="h:q[@display = 'inline']/@display"/>

<!-- blockquote is block display by default  -->
<xsl:template match="h:blockquote[@display = 'block']/@display"/>

<xsl:template match="m:*/@accent"/>

<!-- Remove pgwide attribute. Update style to include width: 100$ if pgwide > 0 -->
<xsl:template match="h:table[@pgwide]">
    <table>
        <xsl:if test="@pgwide > 0">
            <xsl:attribute name="style">
                <xsl:value-of select="@style"/>
                <xsl:text>width: 100%;</xsl:text>
            </xsl:attribute>
        </xsl:if>
        <xsl:apply-templates select="@*[not(name() = 'pgwide')]|node()"/>
    </table>
</xsl:template>

<!-- h6 is the smallest heading -->
<xsl:template match="h:h7|h:h8|h:h9">
    <h6>
        <xsl:apply-templates select="@*|node()"/>
    </h6>
</xsl:template>

<xsl:template match="//h:figure/h:span">
    <div>
        <xsl:apply-templates select="@*|node()"/>
    </div>
</xsl:template>

<xsl:template match="c:para">
    <p>
        <xsl:apply-templates select="@*|node()"/>
    </p>
</xsl:template>

<xsl:template match="@seperators|@separator">
    <xsl:attribute name="separators">
        <xsl:value-of select="."/>
    </xsl:attribute>
</xsl:template>


<xsl:template match="h:figure[*[@data-type='title']]">
    <div data-type="figure-wrapper">
        <xsl:apply-templates select="*[@data-type='title']"/>
        <xsl:copy>
            <xsl:apply-templates select="@*|node()[not(self::*[@data-type='title'])]"/>
        </xsl:copy>
    </div>
</xsl:template>


<xsl:template match="h:dl[h:div]">
    <div data-type="definition-wrapper">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()[not(self::h:div)]"/>
        </xsl:copy>
        <xsl:apply-templates select="h:div"/>
    </div>
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
