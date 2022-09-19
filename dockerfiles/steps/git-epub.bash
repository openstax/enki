parse_book_dir

# set -Eeuxo pipefail

# Get a list of the book slug names
# We assume there will be a file named "{slug}.toc.xhtml"

fetch_root=$IO_FETCHED
IO_DISASSEMBLE_LINKED=$IO_DISASSEMBLE_LINKED
resources_root=$IO_RESOURCES
epub_root=$IO_EPUB
all_slugs=()

# LCOV_EXCL_START
get_item_properties='
<xsl:stylesheet 
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:epub="http://www.idpf.org/2007/ops"
  xmlns:m="http://www.w3.org/1998/Math/MathML"
  xmlns:h="http://www.w3.org/1999/xhtml"
  xmlns="http://www.w3.org/1999/xhtml"
  exclude-result-prefixes="h"
  version="1.0">

<xsl:output method="text"/>

<xsl:template match="/">
    <xsl:if test=".//m:math"><xsl:text>mathml </xsl:text></xsl:if>
    <xsl:if test=".//h:iframe|.//h:object/h:embed"><xsl:text>remote-resources </xsl:text></xsl:if>
    <xsl:if test=".//h:script"><xsl:text>scripted </xsl:text></xsl:if>
</xsl:template>
</xsl:stylesheet>
'
# LCOV_EXCL_END

replace_colons() {
  filename=$1
  filename="${filename//:/-colon-}"
  filename="${filename//@/-at-}"
  filename="${filename//./-dot-}"
  filename="${filename//\//-slash-}"
  echo "${filename}"
}

xpath_sel="//*[@slug]" # All the book entries
while read -r line; do # Loop over each <book> entry in the META-INF/books.xml manifest
    all_slugs+=("$line")

done < <(try xmlstarlet sel -t --match "$xpath_sel" --value-of '@slug' --nl < $fetch_root/META-INF/books.xml)



echo -n 'application/epub+zip' > $epub_root/mimetype

[[ -d "$epub_root/META-INF" ]] || mkdir $epub_root/META-INF
[[ -d "$epub_root/contents" ]] || mkdir $epub_root/contents
[[ -d "$epub_root/contents/resources" ]] || mkdir $epub_root/contents/resources

echo "Generating the META-INF/container.xml file"
echo '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles>' > $epub_root/META-INF/container.xml
# shellcheck disable=SC2068
for slug in ${all_slugs[@]}; do
    echo "    <rootfile media-type=\"application/oebps-package+xml\" full-path=\"contents/$slug.opf\" />" >> $epub_root/META-INF/container.xml
done
echo '</rootfiles></container>' >> $epub_root/META-INF/container.xml

# echo "Validating that META-INF/container.xml is valid XML"
# xmllint $epub_root/META-INF/container.xml > /dev/null


echo "Converting the ToC files"
# shellcheck disable=SC2068
for slug in ${all_slugs[@]}; do
    input_toc_file=$IO_DISASSEMBLE_LINKED/$slug.toc.xhtml
    epub_toc_file=$epub_root/contents/$slug.toc.xhtml

    cat << EOF | xsltproc --output $epub_toc_file /dev/stdin $input_toc_file
<xsl:stylesheet 
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:epub="http://www.idpf.org/2007/ops"
  xmlns:h="http://www.w3.org/1999/xhtml"
  xmlns="http://www.w3.org/1999/xhtml"
  exclude-result-prefixes="h"
  version="1.0">

<!-- Remove ToC entries that have non-Page leaves -->
<xsl:template match="//h:nav//h:li[not(.//h:a)]"/>

<!-- Unwrap chapter links and combine titles into a single span -->
<xsl:template match="h:a[starts-with(@href, &quot;#&quot;)]">
    <span>
        <xsl:apply-templates select="h:span/node()"/>
    </span>
</xsl:template>
<xsl:template match="h:a[not(starts-with(@href, &quot;#&quot;)) and h:span]">
    <xsl:copy>
        <xsl:apply-templates select="@*"/>
        <span>
            <xsl:apply-templates select="h:span/node()"/>
        </span>
    </xsl:copy>
</xsl:template>

<!-- Escape colons in the filename -->
<xsl:template match="@href">
    <xsl:attribute name="href">
        <xsl:call-template name="string-replace-all">
            <xsl:with-param name="text" select="." />
            <xsl:with-param name="replace" select="':'" />
            <xsl:with-param name="by" select="'%3A'" />
        </xsl:call-template>
    </xsl:attribute>
</xsl:template>

<!-- Remove extra attributes -->
<xsl:template match="@cnx-archive-shortid"/>
<xsl:template match="@cnx-archive-uri"/>
<xsl:template match="@itemprop"/>

<!-- XSLT 1.0 does not have a string-replace function (but newer ones do) -->
<xsl:template name="string-replace-all">
    <xsl:param name="text" />
    <xsl:param name="replace" />
    <xsl:param name="by" />
    <xsl:choose>
        <xsl:when test="\$text = '' or \$replace = ''or not(\$replace)" >
            <!-- Prevent this routine from hanging -->
            <xsl:value-of select="\$text" />
        </xsl:when>
        <xsl:when test="contains(\$text, \$replace)">
            <xsl:value-of select="substring-before(\$text,\$replace)" />
            <xsl:value-of select="\$by" />
            <xsl:call-template name="string-replace-all">
                <xsl:with-param name="text" select="substring-after(\$text,\$replace)" />
                <xsl:with-param name="replace" select="\$replace" />
                <xsl:with-param name="by" select="\$by" />
            </xsl:call-template>
        </xsl:when>
        <xsl:otherwise>
            <xsl:value-of select="\$text" />
        </xsl:otherwise>
    </xsl:choose>
</xsl:template>


<!-- Add the epub:type="nav" attribute -->
<xsl:template match="h:nav">
    <nav epub:type="toc" id="toc">
        <xsl:apply-templates select="node()"/>
    </nav>
</xsl:template>

<!-- Recursively copy what is in the source document -->
<xsl:template match="@*|node()">
    <xsl:copy>
        <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
</xsl:template>
</xsl:stylesheet>
EOF

done

echo "Starting the OPF files for each book"
# shellcheck disable=SC2068
for slug in ${all_slugs[@]}; do
    opf_file=$epub_root/contents/$slug.opf
    epub_toc_file=$epub_root/contents/$slug.toc.xhtml

    book_title=$(try jq -r '.title|@html' < $IO_DISASSEMBLE_LINKED/$slug.toc-metadata.json)
    book_lang=$(try jq -r '.language' < $IO_DISASSEMBLE_LINKED/$slug.toc-metadata.json)
    revised_date=$(try jq -r '.revised' < $IO_DISASSEMBLE_LINKED/$slug.toc-metadata.json)
    license=$(try jq -r '.license.url' < $IO_DISASSEMBLE_LINKED/$slug.toc-metadata.json)

    # cnx-usr-books: get collection id from META-INF/books.xml. Referenced in `dcterms:alternative`
    collection_id=$(try xmlstarlet sel -t --match "//*[@collection-id][@slug=\"$slug\"]" --value-of '@collection-id' < "$fetch_root/META-INF/books.xml")

    # HACK get the authors from the original .collection.xml file
    book_href=$(xmlstarlet sel -t --match "//*[@slug=\"$ARG_TARGET_SLUG_NAME\"]" --value-of '@href' --nl < $fetch_root/META-INF/books.xml)

    book_file="$fetch_root/META-INF/$book_href"
    book_authors=$(xmlstarlet sel -t --match "/*" --value-of '@authors' --nl < $book_file)

    # Remove the timezone from the revised_date
    revised_date=${revised_date/+00:00/Z}

    cat << EOF > $opf_file
<?xml version="1.0" encoding="UTF-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>$book_title</dc:title>
    <dc:language>$book_lang</dc:language>
    <meta property="dcterms:modified">$revised_date</meta>
    <meta property="dcterms:license">$license</meta>
    <meta property="dcterms:alternative">$collection_id</meta>
    <dc:identifier id="uid">dummy-cnx.org-id.$slug</dc:identifier>
    <dc:creator>$book_authors</dc:creator>
  </metadata>
  <manifest>
    <item properties="nav" id="nav" href="$slug.toc.xhtml" media-type="application/xhtml+xml" />
    <item id="the-ncx-file" href="$slug.toc.ncx"  media-type="application/x-dtbncx+xml"/>
    <item id="just-the-book-style" href="the-style-epub.css" media-type="text/css" />
EOF

done


extract_html_files_xpath='//*[@href][not(starts-with(@href, "../resources/"))]' # Find XHTML links
extract_resources_xpath_after_cleanup='//h:img/@src|//h:a[starts-with(@href, "resources/")]/@href|//h:object/@data|//h:embed/@src' # Music book links to MP3 & SWF files

echo "Copy CSS file over"
cp "$IO_BAKED/the-style-pdf.css" "$epub_root/contents/the-style-epub.css"

# Copy all directories in resources/ over to contents/resources
shopt -s nullglob   # empty directory will return empty list
for dir in $IO_RESOURCES/*/; do
    cp -r $dir $epub_root/contents/resources/
done
shopt -u nullglob

echo "Starting the bulk of the conversion"
# shellcheck disable=SC2068
for slug in ${all_slugs[@]}; do
    opf_file=$epub_root/contents/$slug.opf
    epub_toc_file=$epub_root/contents/$slug.toc.xhtml
    epub_ncx_file=$epub_root/contents/$slug.toc.ncx

    echo "Find all hrefs in the ToC file"
    html_files=()
    set +e
    hrefs=$(xmlstarlet sel -t --match "$extract_html_files_xpath" --value-of '@href' --nl < $epub_toc_file)
    set -e

    while read -r line; do
        # Unescape those colons again
        line="${line//%3A/:}"
        html_files+=("$line")
    done < <(echo $hrefs) # LCOV_EXCL_LINE

    echo "Convert the ToC XHTML file into an NCX file"
    cat << EOF | xsltproc --output $epub_ncx_file /dev/stdin $epub_toc_file
<xsl:stylesheet 
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:epub="http://www.idpf.org/2007/ops"
  xmlns:h="http://www.w3.org/1999/xhtml"
  xmlns="http://www.daisy.org/z3986/2005/ncx/"
  version="1.0">

<!-- <!DOCTYPE ncx PUBLIC '-//NISO//DTD ncx 2005-1//EN' 'http://www.daisy.org/z3986/2005/ncx-2005-1.dtd'> -->

<xsl:template match="/h:html">
    <xsl:variable name="maxDepth">
        <xsl:choose>
            <xsl:when test="count(//h:nav//h:li//h:li//h:li//h:li//h:li//h:li) > 0">6</xsl:when>
            <xsl:when test="count(//h:nav//h:li//h:li//h:li//h:li//h:li) > 0">5</xsl:when>
            <xsl:when test="count(//h:nav//h:li//h:li//h:li//h:li) > 0">4</xsl:when>
            <xsl:when test="count(//h:nav//h:li//h:li//h:li) > 0">3</xsl:when>
            <xsl:when test="count(//h:nav//h:li//h:li) > 0">2</xsl:when>
            <xsl:when test="count(//h:nav//h:li) > 0">1</xsl:when>
            <xsl:otherwise>0</xsl:otherwise>
        </xsl:choose>
    </xsl:variable>
    <ncx version="2005-1" xml:lang="en">
        <head>
            <meta name="dtb:uid" content="dummy-cnx.org-id.$slug"/>
            <meta name="dtb:depth" content="{\$maxDepth}"/>
            <meta name="dtb:generator" content="OpenStax EPUB Maker 2022-08"/>
            <meta name="dtb:totalPageCount" content="0"/>
            <meta name="dtb:maxPageNumber" content="0"/>
        </head>
        <docTitle><text><xsl:value-of select="h:head/h:title"/></text></docTitle>
        <navMap>
            <xsl:apply-templates select="h:body/h:nav[@epub:type='toc']/h:ol/h:li"/>
        </navMap>
    </ncx>
</xsl:template>

<!-- Leaf node -->
<xsl:template match="h:li[h:a]">
    <xsl:variable name="src" select="h:a/@href"/>
    <navPoint id="{generate-id()}">
        <navLabel><text><xsl:apply-templates select="h:a//text()"/></text></navLabel>
        <content src="{\$src}"/>
    </navPoint>
</xsl:template>

<xsl:template match="h:li[not(h:a)]">
    <xsl:variable name="src" select=".//h:a/@href"/>
    <navPoint id="{generate-id()}">
        <navLabel><text><xsl:apply-templates select="h:span//text()"/></text></navLabel>
        <content src="{\$src[1]}"/>
        <xsl:apply-templates select="h:ol/h:li"/>
    </navPoint>
</xsl:template>

<!-- Identity (to see if anything bleeds through accidentally) -->
<xsl:template match="@*|node()">
    <xsl:copy>
        <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
</xsl:template>

</xsl:stylesheet>
EOF

    all_resources=()

    echo "Processing XHTML files"
    counter=1
    # shellcheck disable=SC2068
    for html_file in ${html_files[@]}; do
        html_file_id="idxhtml_$(replace_colons $html_file)"

        # Copy the file over and clean it up a bit
        input_xhtml_file=$IO_DISASSEMBLE_LINKED/$html_file
        output_xhtml_file=$epub_root/contents/$html_file
        cat << EOF | try xsltproc --output $output_xhtml_file /dev/stdin $input_xhtml_file
<xsl:stylesheet 
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:epub="http://www.idpf.org/2007/ops"
  xmlns:m="http://www.w3.org/1998/Math/MathML"
  xmlns:h="http://www.w3.org/1999/xhtml"
  xmlns="http://www.w3.org/1999/xhtml"
  exclude-result-prefixes="h"
  version="1.0">

<xsl:template match="@itemprop"/>
<xsl:template match="@valign"/>
<xsl:template match="@group-by"/>
<xsl:template match="@use-subtitle"/>
<xsl:template match="h:script"/>
<xsl:template match="h:style"/>

<!-- fix relative resource links for picky epub readers like Apple books -->
<xsl:template match="h:img/@src|h:a[starts-with(@href, '../resources/')]/@href|h:object/@data|h:embed/@src">
    <xsl:choose>
        <xsl:when test="starts-with(., '../resources/')">
            <xsl:attribute name="{name()}">
                <xsl:value-of select="substring(., 4)"/>
            </xsl:attribute>
        </xsl:when>
        <xsl:otherwise>
            <xsl:attribute name="{name()}">
                <xsl:value-of select="."/>
            </xsl:attribute>
        </xsl:otherwise>
    </xsl:choose>
</xsl:template>

<!-- Add a book CSS file -->
<xsl:template match="h:head">
    <xsl:copy>
        <xsl:apply-templates select="@*|node()"/>
        <link rel="stylesheet" type="text/css" href="the-style-epub.css"/>
    </xsl:copy>
</xsl:template>

<!-- re-namespace MathML elements -->
<xsl:template match="h:math|h:math//*">
    <xsl:element name="{local-name()}" namespace="http://www.w3.org/1998/Math/MathML">
        <xsl:apply-templates select="@*|node()"/>
    </xsl:element>
</xsl:template>

<!-- Remove annotation-xml elements because the validator requires an optional "name" attribute -->
<!-- This element is added by https://github.com/openstax/cnx-transforms/blob/85cd5edd5209fcb4c4d72698836a10e084b9ba00/cnxtransforms/xsl/content2presentation-files/cnxmathmlc2p.xsl#L49 -->
<xsl:template match="m:math//m:annotation-xml|h:math//h:annotation-xml"/>

<!-- Recursively copy what is in the source document -->
<xsl:template match="@*|node()">
    <xsl:copy>
        <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
</xsl:template>
</xsl:stylesheet>
EOF

        item_properties=$(echo "$get_item_properties" | try xsltproc /dev/stdin $output_xhtml_file | xargs)

        if [[ $item_properties != '' ]]; then
            item_properties="properties=\"$item_properties\"" # LCOV_EXCL_LINE
        fi

        # Add to OPF spine but HACK the URL so epub readers are not confused
        # Remove leading ./ because ebook readers do not like that in the OPF file
        # Escape those colons again
        fixed_html_file="${html_file//:/%3A}"
        if [[ $fixed_html_file == ./* ]]; then
            fixed_html_file="${fixed_html_file:2}"
        fi

        echo "  <item $item_properties id=\"$html_file_id\" href=\"$fixed_html_file\" media-type=\"application/xhtml+xml\"/>" >> $opf_file
        counter=$((counter+1))

        set +e
        resources_str=$(xmlstarlet sel -N h=http://www.w3.org/1999/xhtml -t --match "$extract_resources_xpath_after_cleanup" --value-of '.' --nl < $output_xhtml_file)
        set -e

        this_resources=()
        while read -r line; do
            this_resources+=("$line")
        done < <(echo $resources_str) # LCOV_EXCL_LINE

        # Add a file extension to the resource file in the XHTML file
        # shellcheck disable=SC2068
        for resource_href in ${this_resources[@]}; do
            resource_filename=$(basename $resource_href)
            resource_file=$epub_root/contents/resources/$resource_filename

            media_type=$(file --brief --mime-type $resources_root/$resource_filename)
            extension='mimetypenotfound'
            case "$media_type" in
                image/jpeg)         extension='jpeg';;
                image/png)          extension='png';;
                # LCOV_EXCL_START
                image/gif)          extension='gif';;
                image/tiff)         extension='tiff';;
                image/svg+xml)      extension='svg';;
                audio/mpeg)         extension='mpg';;
                audio/basic)        extension='au';;
                application/pdf)    extension='pdf';;
                application/zip)    extension='zip';;
                audio/midi)         extension='midi';;
                audio/x-wav)        extension='wav';;
                text/plain)         extension='txt';;
                application/x-shockwave-flash) extension='swf';;
                application/octet-stream)
                    # Try to get the extension from the json file, fall back to bin
                    extension=$(try jq -r '.original_name' "$resources_root/$resource_filename.json" | awk '{
                        ext="bin"
                        idx=index($0, ".")
                        if (idx != 0) {
                            ext=substr($0, idx+1)
                            sub(/^[ \t\r\n]+/, "", ext)
                            sub(/[ \t\r\n]+$/, "", ext)

                            if (length(ext) == 0) {
                                ext="bin"
                            }
                        }
                        print ext
                    }')
                ;;
                *)
                    echo -e "BUG: Add an extension for this mimetype: '$media_type' to this script"
                    exit 2
                ;;
                # LCOV_EXCL_END
            esac

            all_resources+=("$resource_filename.$extension")

            # Add the extension into the XHTML file
            sed --in-place "s/$resource_filename\"/$resource_filename.$extension\"/g" $output_xhtml_file # search with the quotes so we don't double-replace an image

            try cp $resources_root/$resource_filename $resource_file.$extension
            counter=$((counter+1))
        done

    done

    # Remove duplicate resources : https://stackoverflow.com/a/54797762
    all_resources_set=()
    declare -A dupes=()
    for i in "${all_resources[@]}"; do
        if [[ ! ${dupes["$i"]+_} ]]; then # https://stackoverflow.com/a/69041782
            all_resources_set+=("$i")
        fi
        dupes["$i"]=1
    done
    unset dupes # optional
    unset all_resources

    # Add all the resource files (while adding a file extension to the resource file)
    for resource_filename in "${all_resources_set[@]}"; do
        resource_file=$epub_root/contents/resources/$resource_filename

        media_type=$(file --brief --mime-type $resource_file)

        cat << EOF >> $opf_file
    <item id="idresource_$counter" href="resources/$resource_filename" media-type="$media_type"/>
EOF
        counter=$((counter+1))
    done


    echo '</manifest>' >> $opf_file

    # Optionally add the spine (not in order)
    echo "Adding spine"
    cat << EOF >> $opf_file
<spine toc="the-ncx-file"><itemref linear="yes" idref="nav"/>
EOF

    # shellcheck disable=SC2068
    for html_file in ${html_files[@]}; do
        html_file_id="idxhtml_$(replace_colons $html_file)"
        cat << EOF >> $opf_file
    <itemref linear="yes" idref="$html_file_id"/>
EOF
    done

    cat << EOF >> $opf_file
    </spine>
    </package>
EOF

    # Zip up the epub and store it in the artifacts dir
    echo "Zipping EPUB"
    epub_file=$IO_ARTIFACTS/$slug.epub
    [[ -f $epub_file ]] && rm $epub_file
    try cd $epub_root
    try zip -q -X -r $epub_file ./mimetype ./META-INF ./contents
done