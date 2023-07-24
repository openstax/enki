import os
import sys
import json

from .corgi_api import update_job
from .utils import msg


def out(src_path, in_stream):
    input = json.load(in_stream)
    data = input["params"]

    # Remove the id which represents the path in resource.
    # Keep the rest of the information to update the job.
    id_path = data.pop("id")

    msg("Input: {}", input)

    with open(os.path.join(src_path, id_path), "r") as infile:
        id = infile.read()

    artifact_urls = data.get("artifact_urls")
    if artifact_urls:
        with open(os.path.join(src_path, artifact_urls), "r") as infile:
            artifact_url = payload = infile.read()
            try:
                json_payload = json.loads(payload)
                if "View - Rex Web" in payload:
                    data["artifact_urls"] = json_payload[1]["href"] # View - Rex Web Prod
                else:
                    data["artifact_urls"] = json_payload
            except json.JSONDecodeError:
                data["artifact_urls"] = artifact_url

    error_message = data.get("error_message")
    if not error_message:
        error_message_file = data.get("error_message_file")
        if error_message_file:  # pragma: no cover
            full_filepath = os.path.join(src_path, error_message_file)
            with open(full_filepath, "r", errors="replace") as infile:
                error_message_file_data = infile.read()
                data["error_message"] = error_message_file_data
            del data["error_message_file"]

    msg("Params: {}", data)
    msg(f"Updating status of job id {id}")

    response = update_job(input["source"]["api_root"], id, data)

    return {"version": {"id": response["id"]}}


def main():  # pragma: no cover
    src_path = sys.argv[1]
    msg("Source dir {}", src_path)
    print(json.dumps(out(src_path, sys.stdin)))
