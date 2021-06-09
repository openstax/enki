curl "$WEB_FEED_FILE_URL" -o book-feed.json
source /openstax/venv/bin/activate
check-feed book-feed.json "$CODE_VERSION" "$WEB_QUEUE_STATE_S3_BUCKET" "$CODE_VERSION.web-hosting-queue.json" "$MAX_BOOKS_PER_TICK" "archive-dist" "archive"