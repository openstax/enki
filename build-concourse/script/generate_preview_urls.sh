[[ -d $IO_COMMON_LOG ]] || (echo "Undefined Environment variable: IO_COMMON_LOG" && exit 1)
[[ -d $IO_BOOK ]] || (echo "Undefined Environment variable: IO_BOOK" && exit 1)
[[ -d $IO_ARTIFACTS ]] || (echo "Undefined Environment variable: IO_ARTIFACTS" && exit 1)
[[ -d $IO_PREVIEW_URLS ]] || (echo "Undefined Environment variable: IO_PREVIEW_URLS" && exit 1)
[[ $CONTENT_SOURCE ]] || (echo "Undefined Environment variable: CONTENT_SOURCE" && exit 1)
[[ $CORGI_CLOUDFRONT_URL ]] || (echo "Undefined Environment variable: CORGI_CLOUDFRONT_URL" && exit 1)
[[ $CODE_VERSION ]] || (echo "Undefined Environment variable: CODE_VERSION" && exit 1)
[[ $PREVIEW_APP_URL_PREFIX ]] || (echo "Undefined Environment variable: PREVIEW_APP_URL_PREFIX" && exit 1)
[[ $REX_PREVIEW_URL ]] || (echo "Undefined Environment variable: REX_PREVIEW_URL" && exit 1)
[[ $REX_PROD_PREVIEW_URL ]] || (echo "Undefined Environment variable: REX_PROD_PREVIEW_URL" && exit 1)

exec > >(tee $IO_COMMON_LOG/log >&2) 2>&1

case $CONTENT_SOURCE in
    archive)
        collection_id="$(cat $IO_BOOK/collection_id)"
        book_metadata="$IO_ARTIFACTS/collection.toc.json"
        ;;
    git)
        book_slug="$(cat $IO_BOOK/slug)"
        book_metadata="$IO_ARTIFACTS/$book_slug.toc.json"
        ;;
    *)
        echo "CONTENT_SOURCE unrecognized: $CONTENT_SOURCE"
        exit 1
        ;;
esac

book_uuid=$(jq -r '.id' "$book_metadata")
book_version=$(jq -r '.version' "$book_metadata")

rex_archive_param="?archive=${CORGI_CLOUDFRONT_URL}/${PREVIEW_APP_URL_PREFIX}/${CODE_VERSION}"

first_page_slug=$(jq -r '.tree.contents[0].slug' "$book_metadata")
rex_url="${REX_PREVIEW_URL}/books/$book_uuid@$book_version/pages/$first_page_slug$rex_archive_param"
rex_prod_url="${REX_PROD_PREVIEW_URL}/books/$book_uuid@$book_version/pages/$first_page_slug$rex_archive_param"

jq \
    --arg rex_url $rex_url \
    --arg rex_prod_url $rex_prod_url \
    '. + [
        { text: "View - Rex Web", href: $rex_url },
        { text: "View - Rex Web Prod", href: $rex_prod_url }
    ]' \
    <<< '[]' >> $IO_PREVIEW_URLS/content_urls

echo "View web preview here: $rex_url and $rex_prod_url"