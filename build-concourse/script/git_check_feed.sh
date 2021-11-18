curl "$WEB_FEED_FILE_URL" -o book-feed.json
source $PROJECT_ROOT/venv/bin/activate
die "Git feed checker is not implemented yet"
check-feed book-feed.json "$CODE_VERSION" "$WEB_QUEUE_STATE_S3_BUCKET" "$CODE_VERSION.web-hosting-queue.json" "$MAX_BOOKS_PER_TICK" "git-dist" "git"