import os
import sys
import json

from src.cops_api import update_job
from src.utils import msg


def out(src_path, in_stream):
    input = json.load(in_stream)
    data = input["params"]

    # Remove the id which represents the path in resource.
    # Keep the rest of the information to update the job.
    id_path = data.pop("id")

    msg("Input: {}", input)

    with open(os.path.join(src_path, id_path), "r") as infile:
        id = infile.read()

    pdf_url = data.get("pdf_url")
    if pdf_url:
        with open(os.path.join(src_path, pdf_url), "r") as infile:
            pdf_url = infile.read()
            data["pdf_url"] = pdf_url

    error_message = data.get("error_message")
    if not error_message:
        error_message_file = data.get("error_message_file")
        if error_message_file:
            with open(os.path.join(src_path, error_message_file), "r") as infile:
                error_message_file_data = infile.read()
                data["error_message"] = error_message_file_data
            del data["error_message_file"]

    msg("Params: {}", data)
    msg(f"Updating status of job id {id}")

    response = update_job(input["source"]["api_root"], id, data)

    return {"version": {"id": response["id"]}}


def main():
    src_path = sys.argv[1]
    msg("Source dir {}", src_path)
    print(json.dumps(out(src_path, sys.stdin)))
