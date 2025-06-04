SLACK_WEBHOOKS="$( \
    {
        echo "${SLACK_WEBHOOK_CE_STREAM:-}"
        echo "${SLACK_WEBHOOK_UNIFIED:-}"
    } | \
    jq -R 'select(length > 0)' | \
    jq -rs 'join(",")' \
)"
export SLACK_WEBHOOKS

check-feed \
"$CORGI_API_URL" \
"$CODE_VERSION" \
"$WEB_QUEUE_STATE_S3_BUCKET" \
"$CODE_VERSION.$QUEUE_SUFFIX" \
"$MAX_BOOKS_PER_TICK" \
"$STATE_PREFIX"
