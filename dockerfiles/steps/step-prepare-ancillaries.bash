parse_book_dir

shopt -s nullglob

xslt_file="/tmp/transform.xslt"
init_file="/tmp/init.js"
style_file="/tmp/combined-style.css"
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

    <!-- Remove title parts that are irrelevant -->
    <xsl:template match="x:*[@data-type='chapter']/x:*[@data-type='document-title']" />
    <xsl:template match="x:*[@data-type='page']/x:*[@data-type='document-title']/x:*[contains(@class, 'os-number')]" />

    <!-- Update style -->
    <xsl:template match="x:link[@href[substring(., string-length(.) - 7) = '-pdf.css']]/@href">
        <xsl:attribute name="href">./resources/combined-style.css</xsl:attribute>
    </xsl:template>

    <!-- ../resources/... into ./resources/... -->
    <xsl:template match="x:*[@src[starts-with(., '../resources/')]]/@src">
        <xsl:attribute name="src">
            <xsl:value-of select="substring-after(., '.')"/>
        </xsl:attribute>
    </xsl:template>

    <xsl:template match="/x:html/x:head">
        <xsl:copy>
            <xsl:apply-templates />

            <script xmlns="http://www.w3.org/1999/xhtml" type="module" src="./resources/init.js">
                <xsl:comment> no-selfclose </xsl:comment>
            </script>
        </xsl:copy>
    </xsl:template>

</xsl:stylesheet>
EOF

cat - > "$init_file" <<EOF
$(< "$JS_UTILS_STUFF_ROOT/dist/mathjax.js")

/* where one file closes, another opens */

document.addEventListener('DOMContentLoaded', () => {
    void typesetMath(document.body)
});
EOF

# TODO: Probably move this into super pdf style in ce-styles in future
# once it is more clear what these should look like
cat - > "$style_file" <<EOF
$(< "$BOOK_STYLES_ROOT/webview-generic.css")

/* where one file closes, another opens */

:root {
  --content-text-scale: 0.7;
  --body-background-color: #f1f1f1;
  --content-background-color: #fff;
  --content-width: 70%;
  --max-media-width: 65%;
}

body {
  background-color: var(--body-background-color);
  margin-top: 0;
  margin-bottom: 0;
}

body > [data-type=chapter],
body > [data-type=page],
body > [data-type=composite-chapter],
body > [data-type=composite-page] {
  width: var(--content-width);
  margin-left: auto;
  margin-right: auto;
  padding: 2.5rem;
  background-color: var(--content-background-color);
}

[data-type=composite-chapter]:not(:has([data-type=composite-page])) {
  display: none;
}

.os-figure {
  max-width: var(--max-media-width);
}

:not(figure) > [data-type=media]:has(img) {
  max-width: var(--max-media-width);
  margin-left: auto;
  margin-right: auto;
  display: block
}
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
    book_slug="$(basename "$collection" .linked.xhtml)"
    metadata_file="$IO_FETCH_META/super/$book_slug.metadata.json"
    ancillary_dir="$IO_ANCILLARY/$book_slug"
    resources_dir="${ancillary_dir:?}/resources"
    mkdir -p "$resources_dir"
    # Copy collection and all dependencies
    # Retain paths relative to cwd
    smart-copy "$collection" "$(pwd)" "$ancillary_dir"
    # Use new version of the collection
    mv "$ancillary_dir/$(basename "$collection")" "$collection"

    cp "$metadata_file" "$ancillary_dir/metadata.json"
    cp "$style_file" "$resources_dir"
    cp "$init_file" "$resources_dir"
    link-rex "$collection" "$book_slugs_file" "" "$collection.rex-linked.xhtml"
    xsltproc -o "$ancillary_dir/index.html" "$xslt_file" "$collection.rex-linked.xhtml"
    for resource in "$resources_dir"/*; do
        resource_metadata="$IO_RESOURCES/$(basename "$resource").json"
        [ ! -e "$resource_metadata" ] || cp -v "$resource_metadata" "$resources_dir"
    done
done

shopt -u nullglob

