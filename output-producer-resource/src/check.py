import json
import sys

from src.cops_api import get_jobs
from src.utils import msg


def check(in_stream):
    input = json.load(in_stream)
    api_root = input["source"]["api_root"]
    status_id = input["source"].get("status_id")
    job_type_id = input["source"].get("job_type_id")
    version = input.get("version")

    if not status_id:
        return [version] if version else []
    else:
        jobs = get_jobs(api_root)
        msg("jobs: {}", jobs)
        msg("Inputs: {}", input)

        jobs = [job for job in jobs if int(job["status_id"]) == status_id]

        if job_type_id is not None:
            jobs = [job for job in jobs if int(job.get("job_type_id")) == job_type_id]

        if version:
            previous_id = version["id"]
            jobs = [job for job in jobs if int(job["id"]) > int(previous_id)]

        return [{"id": job["id"]} for job in jobs]


def main():
    print(json.dumps(check(sys.stdin)))


if __name__ == "__main__":
    main()
