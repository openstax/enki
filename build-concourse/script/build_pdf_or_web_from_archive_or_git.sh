exec > >(tee $IO_COMMON_LOG/log >&2) 2>&1

book_style="$(cat ./$IO_BOOK/style)"
book_version="$(cat ./$IO_BOOK/version)"

if [[ -f ./$IO_BOOK/repo ]]; then
    book_repo="$(cat ./$IO_BOOK/repo)"
    book_slug="$(cat ./$IO_BOOK/slug)"
    pdf_filename="$(cat ./$IO_BOOK/pdf_filename)"
    if [[ $PDF_OR_WEB == 'pdf' ]]; then
        docker-entrypoint.sh all-git-pdf "$book_repo" "$book_version" "$book_style" "$book_slug"
        docker-entrypoint.sh git-pdfify-meta $S3_ARTIFACTS_BUCKET $pdf_filename

        # Move the PDF and pdf_url into the out directory
        mv /data/artifacts-single/book.pdf $IO_ARTIFACTS_SINGLE/$pdf_filename
        mv /data/artifacts-single/* $IO_ARTIFACTS_SINGLE/
    else # web
        docker-entrypoint.sh all-git-web "$book_repo" "$book_version" "$book_style" "$book_slug"
    fi
else
    book_server="$(cat ./$IO_BOOK/server)"
    book_col_id="$(cat ./$IO_BOOK/collection_id)"

    if [[ $PDF_OR_WEB == 'pdf' ]]; then
        docker-entrypoint.sh all-archive-pdf "$book_col_id" "$book_style" "$book_version" "$book_server" $IO_ARTIFACTS_SINGLE/book.pdf
    else # web
        docker-entrypoint.sh all-archive-web "$book_col_id" "$book_style" "$book_version" "$book_server"
    fi
fi
