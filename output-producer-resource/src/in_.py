import json
import os
import sys

from src import cops_api as api
from src.utils import msg, write_file


def in_(dest_path, in_stream):
    input = json.load(in_stream)
    msg("Input: {}", input)

    api_root = input["source"]["api_root"]
    job_id = input["version"]["id"]

    job = api.get_job(api_root, job_id)
    msg("job Returned: {}", job)

    collection_id = job["collection_id"]
    collection_version = job["version"] or "latest"
    collection_style = job["style"]
    content_server = (job["content_server"] or {"hostname": None})["hostname"]

    # Write out files
    write_file(os.path.join(dest_path, "id"), job_id)
    write_file(os.path.join(dest_path, "collection_id"), collection_id)
    write_file(os.path.join(dest_path, "version"), collection_version)
    write_file(os.path.join(dest_path, "collection_style"), collection_style)
    write_file(os.path.join(dest_path, "content_server"), content_server)
    write_file(os.path.join(dest_path, "job.json"), job)

    return {"version": {"id": job_id}}


def main():
    dest_path = sys.argv[1]
    msg("Output dir {}", dest_path)
    version = in_(dest_path, sys.stdin)
    print(json.dumps(version))


if __name__ == '__main__':
    main()
