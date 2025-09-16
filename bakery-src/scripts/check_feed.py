import os
import json
import sys
from typing import NamedTuple, Any, Optional
from datetime import datetime
from operator import itemgetter
from itertools import groupby

import boto3
import botocore
from .profiler import timed
import requests


COMPLETION_MESSAGE = """
WebHosting Pipeline Status Update

Version: {code_version}
Build Status: Complete ✅
Completion Time: {completion_time}
Books Built: {books_built}
Total Books: {total_books}
Failed Builds: {failed_count}
""".strip()

REVIVAL_MESSAGE = """
WebHosting Pipeline Status Update

Version: {code_version}
Build Status: Running ▶️
Start Time: {start_time}
Books Queued: {books_queued}
""".strip()


def is_status_code(error, status_code):
    return error.response["Error"]["Code"] == status_code


def send_slack_message(message: str):
    api_url = "https://slack.com/api/chat.postMessage"

    def _handle_errors(
        response: requests.Response,
    ) -> Optional[requests.Response]:
        try:
            response.raise_for_status()
            return response
        except Exception as e:
            print(f"Error sending message: {e}", file=sys.stderr)
            return None

    webhooks = (
        webhook.strip()
        for webhook in os.getenv("SLACK_WEBHOOKS", "").split(",")
        if webhook.strip()
    )

    for webhook in webhooks:
        _handle_errors(requests.post(webhook, json={"text": message}))

    post_params_str = os.getenv("SLACK_POST_PARAMS", "")
    if post_params_str:
        try:
            loaded = json.loads(post_params_str)
            if not isinstance(loaded, list):
                post_params_list = [loaded]
            else:
                post_params_list = loaded
            for post_params in post_params_list:
                if not isinstance(post_params, dict):
                    print(
                        f"Invalid post params: {post_params}", file=sys.stderr
                    )
                    continue

                data = {**post_params, "text": message}
                _handle_errors(requests.post(api_url, data=data))
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in SLACK_POST_PARAMS: {e}", file=sys.stderr)


class QueueNotifier(NamedTuple):
    s3_client: Any
    queue_state_bucket: str
    notification_key: str

    def reset(self):
        try:
            self.s3_client.delete_object(
                Bucket=self.queue_state_bucket, Key=self.notification_key
            )
        except botocore.exceptions.ClientError as error:  # pragma: no cover
            if not is_status_code(error, "404"):
                raise

    @property
    def did_notify(self):
        try:
            self.s3_client.head_object(
                Bucket=self.queue_state_bucket, Key=self.notification_key
            )
            return True
        except botocore.exceptions.ClientError as error:
            if is_status_code(error, "404"):
                return False
            else:
                raise  # pragma: no cover

    def notify(self, message: str):
        send_slack_message(message)

    def notify_once(self, message: str):
        if not self.did_notify:
            self.notify(message)
            self.s3_client.put_object(
                Bucket=self.queue_state_bucket,
                Key=self.notification_key,
                Body=datetime.now().astimezone().isoformat(timespec="seconds"),
            )


def unique(it, *, key=hash):
    seen = set()
    for entry in it:
        entry_id = key(entry)
        if entry_id not in seen:
            seen.add(entry_id)
            yield entry


def get_latest_code_version(api_root):
    url = api_root.rstrip("/") + "/api/version/"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def get_is_latest_code_version(api_root, code_version):
    version_json = get_latest_code_version(api_root)
    return version_json["tag"] == code_version


# replace the book feed from github with the accepted books from the ABL endpoint
# somewhere in the pipeline code api_root has the url to the ABL endpoint
# and the code version is passed as an argument
# lets request the ABL endpoint using requests


@timed
def get_abl(api_root, code_version):
    url = api_root.rstrip("/") + "/api/abl/?code_version=" + code_version
    response = requests.get(url)
    is_latest_code_version = get_is_latest_code_version(api_root, code_version)
    response.raise_for_status()
    abl_json = response.json()
    entries = list(
        unique(abl_json, key=itemgetter("repository_name", "commit_sha"))
    )
    # Each edition of a book has a unique uuid
    # This identity scopes to repo + edition
    identity_getter = itemgetter("repository_name", "uuid")
    version_getter = itemgetter("committed_at")
    ranked = {
        identity: list(sorted(group, key=version_getter, reverse=True))
        for identity, group in groupby(entries, key=identity_getter)
    }

    results = []
    for entry in entries:
        latest = ranked[identity_getter(entry)][0]
        book = {}
        book["repo"] = entry["repository_name"]
        book["version"] = entry["commit_sha"]
        book["metadata"] = metadata = {}
        metadata["is_latest"] = (
            is_latest_code_version and
            version_getter(latest) == version_getter(entry)
        )
        results.append(book)

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
    books_complete = 0

    flattened_feed = get_abl(corgi_api_url, code_version)
    total_books = len(flattened_feed)

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
            books_complete += 1
            # Book is complete, move along to next book
            continue
        except botocore.exceptions.ClientError as error:
            if not is_status_code(error, "404"):  # pragma: no cover
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
                if is_status_code(error, "404"):
                    print(f"Found feed entry to build: {book}")
                    # Create new queue version for this book
                    s3_client.put_object(
                        Bucket=queue_state_bucket,
                        Key=queue_filename,
                        Body=json.dumps(book),
                    )
                    # Mark state to not be entered again
                    s3_client.put_object(
                        Bucket=queue_state_bucket,
                        Key=state_key,
                        Body=datetime.now()
                        .astimezone()
                        .isoformat(timespec="seconds"),
                    )
                    books_queued += 1
                    # Book was queued, don't try to queue it again
                    break
                else:  # pragma: no cover
                    # Not an expected 404 error
                    raise

    notifier = QueueNotifier(
        s3_client=s3_client,
        queue_state_bucket=queue_state_bucket,
        notification_key=f"{code_version}/notification.complete",
    )
    if books_queued == 0:
        message = COMPLETION_MESSAGE.format(
            code_version=code_version,
            completion_time=datetime.now().astimezone().isoformat(),
            books_built=books_complete,
            total_books=total_books,
            failed_count=f"{total_books - books_complete}",
        )
        notifier.notify_once(message)
    elif notifier.did_notify:
        message = REVIVAL_MESSAGE.format(
            code_version=code_version,
            start_time=datetime.now().astimezone().isoformat(),
            books_queued=books_queued,
        )
        notifier.notify(message)
        notifier.reset()
    print(f"Queued {books_queued} books")


if __name__ == "__main__":  # pragma: no cover
    main()
