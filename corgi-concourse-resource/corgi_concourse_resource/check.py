import json
import sys

from .corgi_api import get_jobs
from .utils import msg


def check(in_stream):
    input = json.load(in_stream)
    api_root = input["source"]["api_root"]
    status_id = input["source"].get("status_id")
    job_type_id = input["source"].get("job_type_id")
    version = input.get("version")

    if not status_id:
        return [version] if version else []
    else:
        query = {"status_id": status_id}
        if job_type_id is not None:
            query["job_type_id"] = job_type_id
        jobs = get_jobs(api_root, **query)
        msg("jobs: {}", jobs)
        msg("Inputs: {}", input)

        jobs = [{"id": job["id"]} for job in jobs]
        jobs.sort(key=lambda j: j["id"], reverse=True)
        return jobs


def main():  # pragma: no cover
    print(json.dumps(check(sys.stdin)))


if __name__ == "__main__":  # pragma: no cover
    main()
