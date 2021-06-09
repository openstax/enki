exec > >(tee $IO_COMMON_LOG/log >&2) 2>&1

book_style="$(cat ./$IO_BOOK/style)"
book_version="$(cat ./$IO_BOOK/version)"
book_uuid="$(cat ./$IO_BOOK/uuid)"

if [[ -f ./$IO_BOOK/repo ]]; then
    book_repo="$(cat ./$IO_BOOK/repo)"
    book_slug="$(cat ./$IO_BOOK/slug)"
    TRACE_ON=1 docker-entrypoint.sh all-git-web "$book_repo" "$book_version" "$book_style" "$book_slug"
    echo "Git upload not supported yet"
    exit 1
else
    book_server="$(cat ./$IO_BOOK/server)"
    book_col_id="$(cat ./$IO_BOOK/collection_id)"
    TRACE_ON=1 docker-entrypoint.sh all-archive-web "$book_col_id" "$book_style" "$book_version" "$book_server"
    echo "===> Upload book"
    TRACE_ON=1 docker-entrypoint.sh archive-upload-book "$WEB_S3_BUCKET" "$CODE_VERSION"
fi