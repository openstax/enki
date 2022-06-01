parse_book_dir

# Get a list of the book slug names
# We assume there will be a file named "{slug}.toc.xhtml"

fetch_root=$IO_FETCHED
disassembled_root=$IO_DISASSEMBLE_LINKED
resources_root=$IO_RESOURCES
epub_root=$IO_EPUB
all_slugs=()

rewrite_toc_xsl='
<xsl:stylesheet 
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:epub="http://www.idpf.org/2007/ops"
  xmlns:h="http://www.w3.org/1999/xhtml"
  xmlns="http://www.w3.org/1999/xhtml"
  exclude-result-prefixes="h"
  version="1.0">

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

<!-- Remove extra attributes -->
<xsl:template match="@cnx-archive-shortid"/>
<xsl:template match="@cnx-archive-uri"/>
<xsl:template match="@itemprop"/>

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
'

rewrite_xhtml_xsl='
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
'

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
    <xsl:if test=".//h:iframe"><xsl:text>remote-resources </xsl:text></xsl:if>
    <xsl:if test=".//h:script"><xsl:text>scripted </xsl:text></xsl:if>
</xsl:template>
</xsl:stylesheet>
'

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
    IFS=$col_sep read -r slug _ <<< "$line"

    all_slugs+=($slug)

done < <(try xmlstarlet sel -t --match "$xpath_sel" --value-of '@slug' --nl < $fetch_root/META-INF/books.xml)



echo -n 'application/epub+zip' > $epub_root/mimetype

[[ -d "$epub_root/META-INF" ]] || mkdir $epub_root/META-INF
[[ -d "$epub_root/contents" ]] || mkdir $epub_root/contents
[[ -d "$epub_root/resources" ]] || mkdir $epub_root/resources

echo "Generating the META-INF/container.xml file"
echo '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles>' > $epub_root/META-INF/container.xml
for slug in ${all_slugs[@]}; do
    echo "    <rootfile media-type=\"application/oebps-package+xml\" full-path=\"contents/$slug.opf\" />" >> $epub_root/META-INF/container.xml
done
echo '</rootfiles></container>' >> $epub_root/META-INF/container.xml

# echo "Validating that META-INF/container.xml is valid XML"
# xmllint $epub_root/META-INF/container.xml > /dev/null


echo "Converting the ToC files"
for slug in ${all_slugs[@]}; do
    input_toc_file=$disassembled_root/$slug.toc.xhtml
    epub_toc_file=$epub_root/contents/$slug.toc.xhtml

    echo $rewrite_toc_xsl | try xsltproc --output $epub_toc_file /dev/stdin $input_toc_file
done

echo "Starting the OPF files for each book"
for slug in ${all_slugs[@]}; do
    opf_file=$epub_root/contents/$slug.opf
    epub_toc_file=$epub_root/contents/$slug.toc.xhtml

    echo '<?xml version="1.0" encoding="UTF-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="uid">openstax.org.dummy-book-repo.1.0</dc:identifier>
    <dc:title>TODO Extract the title for the book</dc:title>
    <dc:creator>Test user</dc:creator>
    <dc:language>en</dc:language>
    <meta property="dcterms:modified">2020-01-01T00:00:00Z</meta>
  </metadata>
  <manifest>' > $opf_file

  echo "  <item properties=\"nav\" id=\"nav\" href=\"$contents/$slug.toc.xhtml\" media-type=\"application/xhtml+xml\" />" >> $opf_file
done


extract_html_files_xpath='//*[@href]'
extract_resources_xpath='//h:img[@src]'

for slug in ${all_slugs[@]}; do
    opf_file=$epub_root/contents/$slug.opf
    epub_toc_file=$epub_root/contents/$slug.toc.xhtml

    resource_files=()

    html_files=()
    set +e
    hrefs=$(try xmlstarlet sel -t --match "$extract_html_files_xpath" --value-of '@href' --nl < $epub_toc_file)
    set -e

    while read -r line; do
        IFS=$col_sep read -r html_file _ <<< "$line"
        html_files+=($html_file)
    done < <(echo $hrefs)

    counter=1
    for html_file in ${html_files[@]}; do
        html_file_id="idxhtml_$(replace_colons $html_file)"

        # Copy the file over and clean it up a bit
        input_xhtml_file=$disassembled_root/$html_file
        output_xhtml_file=$epub_root/contents/$html_file
        echo $rewrite_xhtml_xsl | try xsltproc --output $output_xhtml_file /dev/stdin $input_xhtml_file

        item_properties=$(echo $get_item_properties | try xsltproc /dev/stdin $output_xhtml_file | xargs)

        if [[ $item_properties != '' ]]; then
            item_properties="properties=\"$item_properties\""
        fi

        # Add to OPF spine
        echo "  <item $item_properties id=\"$html_file_id\" href=\"$html_file\" media-type=\"application/xhtml+xml\"/>" >> $opf_file
        counter=$((counter+1))

        set +e
        resources_str=$(xmlstarlet sel -N h=http://www.w3.org/1999/xhtml -t --match "$extract_resources_xpath" --value-of '@src' --nl < $output_xhtml_file)
        set -e

        resources=()
        while read -r line; do
            IFS=$col_sep read -r resource _ <<< "$line"
            resources+=($resource)
        done < <(echo $resources_str)


        # Add all the resource files
        for resource_href in ${resources[@]}; do
            resource_filename=$(basename $resource_href)
            resource_file=$epub_root/resources/$resource_filename
            try cp $resources_root/$resource_filename $resource_file
            media_type=$(file -b --mime-type $resource_file)
            resource_files+=($resource_file)
            echo "  <item id=\"idresource_$counter\" href=\"../resources/$resource_filename\" media-type=\"$media_type\"/>" >> $opf_file
            counter=$((counter+1))
        done

    done

    echo '</manifest>' >> $opf_file

    # Optionally add the spine (not in order)
    echo "Adding spine"
    echo '<spine>' >> $opf_file
    echo "  <itemref idref=\"nav\"/>" >> $opf_file
    for html_file in ${html_files[@]}; do
        html_file_id="idxhtml_$(replace_colons $html_file)"
        echo "  <itemref idref=\"$html_file_id\"/>" >> $opf_file
    done
    echo '</spine>' >> $opf_file

    echo '</package>' >> $opf_file
done