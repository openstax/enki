import json
import sys
from datetime import datetime

# from pathlib import Path

import boto3
import botocore
from .profiler import timed

import requests

# replace the book feed from github with the accepted books from the ABL endpoint
# somewhere in the pipeline code api_root has the url to the ABL endpoint
# and the code version is passed as an argument
# lets request the ABL endpoint using requests


@timed
def get_abl(api_root, code_version):
    url = api_root.rstrip("/") + "/api/abl/?code_version=" + code_version
    response = requests.get(url)
    response.raise_for_status()
    abl_json = response.json()
    results = [
        {"repo": entry["repository_name"], "version": entry["commit_sha"]}
        for entry in abl_json
    ]
    return results


@timed
def main():
    corgi_api_url = sys.argv[1]
    code_version = sys.argv[2]
    queue_state_bucket = sys.argv[3]
    queue_filename = sys.argv[4]
    max_books_per_run = int(sys.argv[5])
    state_prefix = sys.argv[6]

    s3_client = boto3.client("s3")
    books_queued = 0

    flattened_feed = get_abl(corgi_api_url, code_version)

    # Iterate through feed and check for a book that is not completed based
    # upon existence of a {code_version}/.{collection_id}@{version}.complete
    # file in S3 bucket. If the book is not complete, check pending and retry
    # states to see whether or not it has errored or timed out too many times
    # to be queued again.

    for book in flattened_feed:
        # Check for loop exit condition
        if books_queued >= max_books_per_run:
            break

        book_identifier = book["repo"]
        book_version = book["version"]

        book_prefix = f".{state_prefix}.{book_identifier}@{book_version}"
        complete_key = f"{code_version}/{book_prefix}.complete"

        try:
            print(f"Checking for s3://{queue_state_bucket}/{complete_key}")
            s3_client.head_object(Bucket=queue_state_bucket, Key=complete_key)
            # Book is complete, move along to next book
            continue
        except botocore.exceptions.ClientError as error:
            error_code = error.response["Error"]["Code"]
            if error_code != "404":  # pragma: no cover
                # Not an expected 404 error
                raise
            # Otherwise, book is not complete and we check other states

        # These states are order-dependant.
        # i.e. only move to retry if pending passes through
        for state in ["pending", "retry"]:
            state_filename = f"{book_prefix}.{state}"
            state_key = f"{code_version}/{state_filename}"
            try:
                print(f"Checking for s3://{queue_state_bucket}/{state_key}")
                s3_client.head_object(Bucket=queue_state_bucket, Key=state_key)
            except botocore.exceptions.ClientError as error:
                error_code = error.response["Error"]["Code"]
                if error_code == "404":
                    print(f"Found feed entry to build: {book}")
                    s3_client.put_object(
                        Bucket=queue_state_bucket,
                        Key=queue_filename,
                        Body=json.dumps(book),
                    )
                    # Mark state to not be entered again
                    s3_client.put_object(
                        Bucket=queue_state_bucket,
                        Key=state_key,
                        Body=datetime.now().astimezone().isoformat(timespec="seconds"),
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
