set -Eeuo pipefail

validator_jar=$PROJECT_ROOT/epub-validator/epubcheck-$EPUB_VALIDATOR_VERSION/epubcheck.jar

shopt -s globstar nullglob
for epub_file in "$IO_ARTIFACTS/"*.epub; do

    echo "Validating $epub_file"
    epub_filename=$(basename "$epub_file")

    set +e
    java -jar $validator_jar --error $epub_file 2> $IO_ARTIFACTS/$epub_filename.validation.log
    exit_status=$?

    [[ ! -f $IO_ARTIFACTS/$epub_filename.validation.log ]] && die "$IO_ARTIFACTS/$epub_filename.validation.log does not exist"

    if [[ $exit_status != 0 ]]; then
        # LCOV_EXCL_START
        # errors=$(cat $IO_ARTIFACTS/$epub_filename.validation.log | grep 'ERROR' \
        #     | grep -v 'Error while parsing file: element "mrow" not allowed here;' \
        #     | grep -v 'Error while parsing file: element "mn" not allowed here;' \
        #     | grep -v 'Error while parsing file: element "minus" not allowed here;' \
        #     | grep -v 'Error while parsing file: element "or" not allowed here;' \
        #     | grep -v 'The type property "application/vnd.wolfram.cdf" on the object tag does not match the declared media-type "text/plain" in the OPF manifest.' \
        #     | grep -v 'of type "text/plain"' \
        #     | grep -v 'ERROR(RSC-010)' \
        #     | grep -v 'ERROR(RSC-012)' \
        #     | grep -v 'ERROR(MED-002)' \
        # )
        errors=$(cat $IO_ARTIFACTS/$epub_filename.validation.log | grep 'ERROR' \
            | grep -v '.epub/the-style-epub.css' \
            | grep -v 'Error while parsing file: element "aside" not allowed here' \
            | grep -v 'Error while parsing file: attribute "longdesc" not allowed here' \
            | grep -v 'Error while parsing file: attribute "summary" not allowed here;' \
            ;
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

done
shopt -u globstar nullglob
