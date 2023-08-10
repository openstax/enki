import json
import os
import sys

from . import corgi_api as api
from .utils import msg, write_file, get_repo_path


def in_(dest_path, in_stream):
    input = json.load(in_stream)
    msg("Input: {}", input)

    api_root = input["source"]["api_root"]
    job_id = input["version"]["id"]

    job = api.get_job(api_root, job_id)
    msg("job Returned: {}", job)

    repo_path = get_repo_path(job)
    collection_version = job["version"] or "latest"
    slugs = "\n".join(b["slug"] for b in job["books"])

    # Write out files
    write_file(os.path.join(dest_path, "id"), job_id)
    write_file(os.path.join(dest_path, "repo"), repo_path)
    write_file(os.path.join(dest_path, "slugs"), slugs)
    write_file(os.path.join(dest_path, "version"), collection_version)
    write_file(os.path.join(dest_path, "job.json"), job)

    return {"version": {"id": job_id}}


def main():  # pragma: no cover
    dest_path = sys.argv[1]
    msg("Output dir {}", dest_path)
    version = in_(dest_path, sys.stdin)
    print(json.dumps(version))


if __name__ == '__main__':  # pragma: no cover
    main()
