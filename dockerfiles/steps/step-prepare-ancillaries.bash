parse_book_dir

shopt -s nullglob

xslt_file="/tmp/transform.xslt"
book_slugs_file="/tmp/book-slugs.json"

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

repo_root=$IO_FETCH_META
col_sep='|'
xpath_sel="//*[@slug]" # All the book entries
while IFS=$col_sep read -r slug href _style; do # Loop over each <book> entry in the META-INF/books.xml manifest
    path="$repo_root/META-INF/$href"

    uuid=$(xmlstarlet sel -t --match "//*[local-name()='uuid']" --value-of 'text()' < $path)
    jq -n "{ slug: \"$slug\", uuid: \"$uuid\" }" >> $book_slugs_file

    # --------- Code ends here
done < <(xmlstarlet sel -t --match "$xpath_sel" --value-of '@slug' --value-of "'$col_sep'" --value-of '@href' --value-of "'$col_sep'" --value-of '@style' --nl < $repo_root/META-INF/books.xml)

jq -s . $book_slugs_file > $book_slugs_file.tmp && mv $book_slugs_file.tmp $book_slugs_file

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
    # Use new version of the collection
    collection="$ancillary_dir/$(basename "$collection")"

    cp "$metadata_file" "$ancillary_dir/metadata.json"
    cp "$BOOK_STYLES_ROOT/webview-generic.css" "$resources_dir"
    link-rex "$collection" "$book_slugs_file" "" "$collection.rex-linked.xhtml"
    xsltproc -o "$ancillary_dir/index.html" "$xslt_file" "$collection.rex-linked.xhtml"
    for resource in "$resources_dir"/*; do
        resource_metadata="$IO_RESOURCES/$(basename "$resource").json"
        [ ! -e "$resource_metadata" ] || cp -v "$resource_metadata" "$resources_dir"
    done
done

shopt -u nullglob

