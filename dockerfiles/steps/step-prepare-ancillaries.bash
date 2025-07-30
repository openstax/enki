parse_book_dir

shopt -s nullglob

xslt_file="$(realpath ./transform.xslt)"

# TODO: Maybe move this into a file
cat - > "$xslt_file" <<EOF
<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:x="http://www.w3.org/1999/xhtml">

    <xsl:template match="@*|node()">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
    </xsl:template>

    <!-- ../resources/... into ./resources/... -->
    <xsl:template match="x:*[@src[starts-with(., '../resources/')]]/@src">
        <xsl:attribute name="src">
            <xsl:value-of select="substring-after(., '.')"/>
        </xsl:attribute>
    </xsl:template>

</xsl:stylesheet>
EOF

pattern='//x:*[@src][starts-with(@src, ".")]/@src'
for collection in "$IO_SUPER/"*.linked.xhtml; do
    slug_name="$(basename "$collection" .linked.xhtml)"
    # super-<uuid>
    module_uuid="${slug_name:6}"
    metadata_file="$IO_FETCH_META/super/$module_uuid.metadata.json"
    ancillary_dir="$IO_ANCILLARY/$module_uuid"
    resources_dir="$ancillary_dir/resources"
    mkdir -p "$ancillary_dir" "$resources_dir"
    xmlstarlet sel \
        -N "x=http://www.w3.org/1999/xhtml" \
        --template \
        --match "$pattern" \
        --value-of '.' \
        --nl \
        "$collection" || true | \
    awk '{ sub("../resources", "../IO_RESOURCES"); print }' | \
    xargs -d$'\n' bash -c '[[ $# -eq 0 ]] || cp -rv "$@" "'"$resources_dir"'"' bash

    cp "$metadata_file" "$ancillary_dir"
    xsltproc "$xslt_file" "$collection" > "$ancillary_dir/$module_uuid.xhtml"
done

shopt -u nullglob

