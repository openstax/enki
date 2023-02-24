import json
import sys
from datetime import datetime
from pathlib import Path

import boto3
import botocore


def is_number(s):  # pragma: no cover
    try:
        float(s)
        return True
    except ValueError:
        pass
    return False


def flatten_feed(feed_data, feed_filter, code_version):
    ARCHIVE_BOOK_ID_KEY = "collection_id"
    GIT_BOOK_ID_KEY = "repository_name"

    def _is_archive_entry(entry):
        return entry.get(ARCHIVE_BOOK_ID_KEY) is not None

    def _is_git_entry(entry):
        return entry.get(GIT_BOOK_ID_KEY) is not None

    def _convert_archive_entry(book, version):
        # Archive approved book items should only have a single book entry
        return [{
            "collection_id": book[ARCHIVE_BOOK_ID_KEY],
            "server": book["server"],
            "style": book["style"],
            "uuid": book["books"][0]["uuid"],
            "slug": book["books"][0]["slug"],
            "version": version
        }]

    books_by_id = {}
    flattened_feed = []

    if feed_filter == "archive":
        filter_function = _is_archive_entry
        convert_function = _convert_archive_entry
        book_id_key = ARCHIVE_BOOK_ID_KEY
    elif feed_filter == "git":
        filter_function = _is_git_entry
        book_id_key = GIT_BOOK_ID_KEY
    else:
        # An unexpected filter value.
        raise Exception("Invalid feed filter value")

    approved_books = list(filter(
        filter_function,
        feed_data["approved_books"]
    ))

    approved_versions = filter(
        filter_function,
        feed_data["approved_versions"]
    )

    for item in approved_books:
        book_id = item[book_id_key]
        books_by_id[book_id] = item

    if feed_filter == "archive":
        for item in approved_versions:
            book_id = item[book_id_key]
            book = books_by_id[book_id]
            if code_version >= item["min_code_version"]:
                flattened_feed += convert_function(book,
                                                   item["content_version"])

    if feed_filter == "git":
        # item = {
        #     repository_name: "osbooks-college-algebra-bundle",
        #     versions: [
        #     {
        #         min_code_version: "20210224.204120",
        #         commit_sha: "cede276a22287dd000406feb1c0e112af168aef9",
        #           ...

        if not is_number(code_version):  # pragma: no cover
            print('----------------------------')
            print('Ignoring min_code_version because code_version')
            print(f"  is not a number '{code_version}' (dev testing)")
            print('----------------------------')
            code_version = 99999999  # 9999-99-99

        for item in approved_books:
            repository_name = item[GIT_BOOK_ID_KEY]
            for version in item["versions"]:
                min_code_version = version["min_code_version"]
                commit_sha = version["commit_sha"]
                if code_version >= min_code_version:
                    flattened_feed.append({
                        "repo": repository_name,
                        "version": commit_sha
                    })
                else:  # pragma: no cover
                    print(
                        "Skipping entry because codeversion is too new. "
                        f"This pipeline codeversion: {code_version}. "
                        f"min_code_version for the ABL entry: {min_code_version}"
                    )

    # flattened_feed format
    # {
    #     "repo": book[GIT_BOOK_ID_KEY],
    #     "uuid": repo_book["uuid"],
    #     "slug": repo_book["slug"],
    #     "version": version
    # }

    return flattened_feed


def main():
    feed_json = Path(sys.argv[1]).resolve(strict=True)
    code_version = sys.argv[2]
    queue_state_bucket = sys.argv[3]
    queue_filename = sys.argv[4]
    max_books_per_run = int(sys.argv[5])
    state_prefix = sys.argv[6]
    feed_filter = sys.argv[7]

    with open(feed_json, 'r') as feed_file:
        feed_data = json.load(feed_file)

    s3_client = boto3.client('s3')
    books_queued = 0

    flattened_feed = flatten_feed(feed_data, feed_filter, code_version)

    # Iterate through feed and check for a book that is not completed based
    # upon existence of a {code_version}/.{collection_id}@{version}.complete
    # file in S3 bucket. If the book is not complete, check pending and retry
    # states to see whether or not it has errored or timed out too many times
    # to be queued again.

    for book in flattened_feed:
        # Check for loop exit condition
        if books_queued >= max_books_per_run:
            break

        book_identifier = book.get('collection_id', book.get('repo'))

        book_prefix = \
            f".{state_prefix}.{book_identifier}@{book['version']}"

        complete_filename = f"{book_prefix}.complete"
        complete_key = f"{code_version}/{complete_filename}"
        try:
            print(f"Checking for s3://{queue_state_bucket}/{complete_key}")
            s3_client.head_object(
                Bucket=queue_state_bucket,
                Key=complete_key
            )
            # Book is complete, move along to next book
            continue
        except botocore.exceptions.ClientError as error:
            error_code = error.response['Error']['Code']
            if error_code != '404':  # pragma: no cover
                # Not an expected 404 error
                raise
            # Otherwise, book is not complete and we check other states

        # These states are order-dependant.
        # i.e. only move to retry if pending passes through
        for state in ['pending', 'retry']:
            state_filename = f"{book_prefix}.{state}"
            state_key = f"{code_version}/{state_filename}"
            try:
                print(f"Checking for s3://{queue_state_bucket}/{state_key}")
                s3_client.head_object(
                    Bucket=queue_state_bucket,
                    Key=state_key
                )
            except botocore.exceptions.ClientError as error:
                error_code = error.response['Error']['Code']
                if error_code == '404':
                    print(f"Found feed entry to build: {book}")
                    s3_client.put_object(
                        Bucket=queue_state_bucket,
                        Key=queue_filename,
                        Body=json.dumps(book)
                    )
                    # Mark state to not be entered again
                    s3_client.put_object(
                        Bucket=queue_state_bucket,
                        Key=state_key,
                        Body=datetime.now().astimezone().isoformat(
                            timespec='seconds'
                        )
                    )
                    books_queued += 1
                    # Book was queued, don't try to queue it again
                    break
                else:  # pragma: no cover
                    # Not an expected 404 error
                    raise

    print(f"Queued {books_queued} books")


if __name__ == "__main__":  # pragma: no cover
    main()
