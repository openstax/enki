parse_book_dir

shopt -s nullglob

xslt_file="$(realpath ./transform.xslt)"

# TODO: Maybe move this into a file
cat - > "$xslt_file" <<EOF
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:x="http://www.w3.org/1999/xhtml"
>

    <xsl:output omit-xml-declaration="yes"/>

    <xsl:template match="@*|node()">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
    </xsl:template>

    <!-- Remove nav -->
    <xsl:template match="x:nav" />

    <!-- Update style -->
    <xsl:template match="x:link[@href[substring(., string-length(.) - 7) = '-pdf.css']]/@href">
        <xsl:attribute name="href">./resources/webview-generic.css</xsl:attribute>
    </xsl:template>

    <!-- ../resources/... into ./resources/... -->
    <xsl:template match="x:*[@src[starts-with(., '../resources/')]]/@src">
        <xsl:attribute name="src">
            <xsl:value-of select="substring-after(., '.')"/>
        </xsl:attribute>
    </xsl:template>

</xsl:stylesheet>
EOF

for collection in "$IO_SUPER/"*.linked.xhtml; do
    module_uuid="$(
        echo "$collection" |
        tr '[:upper:]' '[:lower:]' |
        grep -Eo '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    )"
    metadata_file="$IO_FETCH_META/super/$module_uuid.metadata.json"
    ancillary_dir="$IO_ANCILLARY/$module_uuid"
    resources_dir="${ancillary_dir:?}/resources"
    mkdir -p "$resources_dir"
    # Copy collection and all dependencies
    # Retain paths relative to cwd
    smart-copy "$collection" "$(pwd)" "$ancillary_dir"

    cp "$metadata_file" "$ancillary_dir/metadata.json"
    cp "$BOOK_STYLES_ROOT/webview-generic.css" "$resources_dir"
    xsltproc -o "$ancillary_dir/index.html" "$xslt_file" "$collection"
    # A side-effect of smart-copy is copying the "super" directory
    # We don't actually need this since we use the index.html created above
    rm -r "${ancillary_dir:?}/$(realpath --relative-to "$(pwd)" "$IO_SUPER")"
done

shopt -u nullglob

