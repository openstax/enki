shopt -s globstar nullglob
# Create an empty map file for invoking assemble-meta
echo "{}" > uuid-to-revised-map.json
for collection in "$IO_ASSEMBLED/"*.assembled.xhtml; do
    slug_name=$(basename "$collection" | awk -F'[.]' '{ print $1; }')
    try assemble-meta "$IO_ASSEMBLED/$slug_name.assembled.xhtml" uuid-to-revised-map.json "$IO_ASSEMBLE_META/$slug_name.assembled-metadata.json"

    try xsltproc --output "temp-phil.xhtml" /dev/stdin "$IO_ASSEMBLED/$slug_name.assembled.xhtml" << EOF
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

EOF

    mv "temp-phil.xhtml" "$IO_ASSEMBLED/$slug_name.assembled.xhtml"

done
try rm uuid-to-revised-map.json
shopt -u globstar nullglob
