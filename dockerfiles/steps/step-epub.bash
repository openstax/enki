# Formerly git-epub
parse_book_dir

set -Eeuxo pipefail
# Ensure $IO_EPUB is empty
[[ -d $IO_EPUB ]] && rm -rf ${IO_EPUB:?}/*
node --unhandled-rejections=strict "$JS_UTILS_STUFF_ROOT/bin/bakery-helper" epub ./ "$IO_EPUB/"

shopt -s globstar nullglob
for book_dir in "$IO_EPUB/"*; do

    slug_name=$(basename "$book_dir")
    # Paths are relative in concourse.
    # Make this path absolute before changing directories
    epub_file_path="$(realpath "$IO_ARTIFACTS/$slug_name.epub")"
    pushd "$book_dir"
    zip "$epub_file_path" -DX0 mimetype
    zip "$epub_file_path" -DX9 META-INF/container.xml
    zip "$epub_file_path" -DX9 ./*
    popd
done

# Formerly git-epub-validate
set -Eeuo pipefail

validator_jar=$PROJECT_ROOT/epub-validator/epubcheck-$EPUB_VALIDATOR_VERSION/epubcheck.jar

# shopt -s globstar nullglob
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
            | grep -v 'Error while parsing file: attribute "display" not allowed here;' \
            | grep -v 'Error while parsing file: value of attribute "target" is invalid;' \
            | grep -v 'Error while parsing file: value of attribute "colspan" is invalid;' \
            \
            | grep -v 'Error while parsing file: value of attribute "width" is invalid;' \
            | grep -v 'Error while parsing file: value of attribute "height" is invalid;' \
            | grep -v 'Error while parsing file: element "aside" not allowed here' \
            | grep -v 'Error while parsing file: attribute "longdesc" not allowed here' \
            | grep -v 'Error while parsing file: attribute "summary" not allowed here;' \
            \
            | grep -v 'Error while parsing file: attribute "rules" not allowed here;' \
            | grep -v 'Error while parsing file: attribute "align" not allowed here;' \
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
