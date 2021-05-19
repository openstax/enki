exec > >(tee $IO_COMMON_LOG/log >&2) 2>&1

[[ -d $IO_COMMON_LOG ]] || (echo "Undefined Environment variable: IO_COMMON_LOG" && exit 1)
[[ -d $IO_BOOK ]] || (echo "Undefined Environment variable: IO_BOOK" && exit 1)
[[ -d $IO_ARTIFACTS_SINGLE ]] || (echo "Undefined Environment variable: IO_ARTIFACTS_SINGLE" && exit 1)
[[ $PDF_OR_WEB ]] || (echo "Undefined Environment variable: PDF_OR_WEB" && exit 1)
[[ $CORGI_ARTIFACTS_S3_BUCKET ]] || (echo "Undefined Environment variable: CORGI_ARTIFACTS_S3_BUCKET" && exit 1)
[[ $CODE_VERSION ]] || (echo "Undefined Environment variable: CODE_VERSION" && exit 1)
[[ $REX_PREVIEW_URL ]] || (echo "Undefined Environment variable: REX_PREVIEW_URL" && exit 1)
[[ $REX_PROD_PREVIEW_URL ]] || (echo "Undefined Environment variable: REX_PROD_PREVIEW_URL" && exit 1)


book_style="$(cat ./$IO_BOOK/style)"
book_version="$(cat ./$IO_BOOK/version)"

if [[ -f ./$IO_BOOK/repo ]]; then
    book_repo="$(cat ./$IO_BOOK/repo)"
    book_slug="$(cat ./$IO_BOOK/slug)"
    if [[ $PDF_OR_WEB == 'pdf' ]]; then
        pdf_filename="$(cat ./$IO_BOOK/pdf_filename)"

        docker-entrypoint.sh all-git-pdf "$book_repo" "$book_version" "$book_style" "$book_slug"
        docker-entrypoint.sh git-pdfify-meta $CORGI_ARTIFACTS_S3_BUCKET $pdf_filename

        # Move the PDF and pdf_url into the out directory
        if [[ -f ./book.pdf ]]; then # Old location
            mv ./book.pdf $IO_ARTIFACTS_SINGLE/$pdf_filename
        else
            mv /data/artifacts-single/book.pdf $IO_ARTIFACTS_SINGLE/$pdf_filename
        fi
        mv /data/artifacts-single/* $IO_ARTIFACTS_SINGLE/
    else # web
        docker-entrypoint.sh all-git-web "$book_repo" "$book_version" "$book_style" "$book_slug"
        docker-entrypoint.sh git-upload-book "$CORGI_ARTIFACTS_S3_BUCKET" "$CODE_VERSION" "$book_slug"

        # Move the JSON artifacts into the IO_ARTIFACTS_SINGLE directory
        mv /data/jsonified-single/* $IO_ARTIFACTS_SINGLE/
    fi
else
    book_server="$(cat ./$IO_BOOK/server)"
    book_col_id="$(cat ./$IO_BOOK/collection_id)"

    if [[ $PDF_OR_WEB == 'pdf' ]]; then
        pdf_filename="$(cat ./$IO_BOOK/pdf_filename)"

        docker-entrypoint.sh all-archive-pdf "$book_col_id" "$book_style" "$book_version" "$book_server" $IO_ARTIFACTS_SINGLE/book.pdf

        # Move the PDF and pdf_url into the out directory
        mv /data/assembled/collection.pdf $IO_ARTIFACTS_SINGLE/$pdf_filename
        echo -n "https://$CORGI_ARTIFACTS_S3_BUCKET.s3.amazonaws.com/$pdf_filename" >$IO_ARTIFACTS_SINGLE/pdf_url

    else # web
        docker-entrypoint.sh all-archive-web "$book_col_id" "$book_style" "$book_version" "$book_server"
        docker-entrypoint.sh archive-upload-book "$CORGI_ARTIFACTS_S3_BUCKET" "$CODE_VERSION"

        # Move the JSON artifacts into the IO_ARTIFACTS_SINGLE directory
        mv /data/jsonified/* $IO_ARTIFACTS_SINGLE/

    fi
fi
