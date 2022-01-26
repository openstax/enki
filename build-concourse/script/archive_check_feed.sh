curl "$ABL_FILE_URL" -o book-feed.json
source $VENV_ROOT/bin/activate
check-feed book-feed.json "$CODE_VERSION" "$WEB_QUEUE_STATE_S3_BUCKET" "$CODE_VERSION.web-hosting-archive-queue.json" "$MAX_BOOKS_PER_TICK" "archive-dist" "archive"