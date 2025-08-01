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

    <!-- Promote title to h1 -->
    <xsl:template match="x:div[@data-type='page']/x:div[@data-type='document-title']">
        <xsl:element name="h1" namespace="http://www.w3.org/1999/xhtml">
            <xsl:apply-templates select="@*|node()"/>
        </xsl:element>
    </xsl:template>

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
    slug_name="$(basename "$collection" .linked.xhtml)"
    # super-<uuid>
    module_uuid="${slug_name:6}"
    metadata_file="$IO_FETCH_META/super/$module_uuid.metadata.json"
    ancillary_dir="$IO_ANCILLARY/$module_uuid"
    resources_dir="$ancillary_dir/resources"
    mkdir -p "$ancillary_dir" "$resources_dir"
    { 
        xmlstarlet sel \
            -N "x=http://www.w3.org/1999/xhtml" \
            --template \
            --match '//x:*[@src][starts-with(@src, ".")]/@src' \
            --value-of '.' \
            --nl \
            "$collection" || true
    } | \
    awk \
        -v "resources_dir=$IO_RESOURCES" \
        -v "dom_resource_path=../resources" \
        '{ sub(dom_resource_path, resources_dir); print }' | \
    xargs -d$'\n' bash -ec '[[ $# -eq 0 ]] || cp -rv "$@" "'"$resources_dir"'"' bash

    for f in "$resources_dir"/*; do
        resource_metadata_file="$IO_RESOURCES/$(basename "$f").json"
        if [[ -f "$resource_metadata_file" ]]; then
            cp "$resource_metadata_file" "$resources_dir"
        fi
    done

    cp "$metadata_file" "$ancillary_dir/metadata.json"
    cp "$BOOK_STYLES_ROOT/webview-generic.css" "$resources_dir"
    xsltproc -o "$ancillary_dir/index.html" "$xslt_file" "$collection"
done

shopt -u nullglob

