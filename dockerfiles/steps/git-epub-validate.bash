src_dir=$IO_EPUB
epub_file=/tmp/test.epub
validator_jar=$PROJECT_ROOT/epub-validator/epubcheck-$EPUB_VALIDATOR_VERSION/epubcheck.jar

[[ -f $epub_file ]] && rm $epub_file

try cd $src_dir
try zip -q -X -r $epub_file ./mimetype ./META-INF ./contents ./resources ./the-style-epub.css


set +e
java -jar $validator_jar --error $epub_file 2> $IO_EPUB/validation.log
exit_status=$?
set -e

if [[ $exit_status != 0 ]]; then
    errors=$(cat $IO_EPUB/validation.log | grep 'ERROR' \
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
    error_count=$(echo "$errors" | wc -l)
    if [[ $error_count != 0 ]]; then
        echo "$errors"
        die "Failed to validate: $error_count errors that we have not chosen to ignore"
    else
        echo "Yay! No errors besides the ones we have already chosen to ignore"
    fi
fi