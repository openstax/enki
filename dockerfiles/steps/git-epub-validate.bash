src_dir=$IO_EPUB
epub_file=$IO_ARTIFACTS/book.epub
validator_jar=$PROJECT_ROOT/epub-validator/epubcheck-$EPUB_VALIDATOR_VERSION/epubcheck.jar

set +e
java -jar $validator_jar --error $epub_file 2> $IO_ARTIFACTS/validation.log
exit_status=$?

[[ ! -f $IO_ARTIFACTS/validation.log ]] && die "$IO_ARTIFACTS/validation.log does not exist"

if [[ $exit_status != 0 ]]; then
    # LCOV_EXCL_START
    errors=$(cat $IO_ARTIFACTS/validation.log | grep 'ERROR' \
        | grep -v 'ERROR(RSC-012)' \
        | grep -v 'ERROR(MED-002)' \
        | grep -v 'Error while parsing file: element "mrow" not allowed here;' \
        | grep -v 'Error while parsing file: element "mn" not allowed here;' \
        | grep -v 'Error while parsing file: element "minus" not allowed here;' \
        | grep -v 'Error while parsing file: element "or" not allowed here;' \
        | grep -v 'The type property "application/vnd.wolfram.cdf" on the object tag does not match the declared media-type "text/plain" in the OPF manifest.' \
        | grep -v 'of type "text/plain"' \
        | grep -v 'ERROR(RSC-010)' \
    )
    if [[ $errors ]]; then
        echo "$errors"
        die "Failed to validate: $(echo "$errors" | wc -l) errors that we have not chosen to ignore"
    else
        echo "Yay! No errors besides the ones we have already chosen to ignore"
    fi
    # LCOV_EXCL_END
fi
set -e



# EPUB Readers are picky with colons and ./ in paths to files so we check for epub-reader specific problems here:
while read -r opf_file_path; do
    opf_file=$src_dir/$opf_file_path

        cat << EOF | xsltproc /dev/stdin $opf_file
<xsl:stylesheet 
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:opf="http://www.idpf.org/2007/opf"
  version="1.0">

<xsl:template match="/opf:package/opf:manifest/opf:item">
    <xsl:if test="starts-with(@href, './')"><xsl:message terminate="yes">Some ePub Readers do not like hrefs that begin with './'</xsl:message></xsl:if>
    <xsl:if test="contains(@href, ':')"><xsl:message terminate="yes">Some ePub Readers do not like filenames that contain a colon ':'./</xsl:message></xsl:if>
</xsl:template>

<xsl:template match="@*|node()">
    <xsl:apply-templates select="@*|node()"/>
</xsl:template>

</xsl:stylesheet>
EOF


done < <(try xmlstarlet sel -t --match "//*[@full-path]" --value-of '@full-path' --nl < $src_dir/META-INF/container.xml)
