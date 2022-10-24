"""This is a utility script used to initialize a local COPS environment for
recording vcr cassettes. See README.md for use of this script.
"""

import sys
import requests

API_ROOT = "http://localhost/api"


def main():
    cookie = sys.argv[1]
    url = f"{API_ROOT}/jobs"

    data = {
        "status_id": "1",
        "job_type_id": "1",
        "version": None,
        "worker_version": "1",
        "repository": {
            "name": "osbooks-college-success",
            "owner": "openstax"
        },
        "book": None,
        "style": None
    }

    # Generate various permutations of job types and states
    for status_id in ["1", "2", "3", "4", "5"]:
        for job_type_id in ["3", "4", "5"]:
            data["status_id"] = status_id
            data["job_type_id"] = job_type_id

            response = requests.post(url, json=data, headers={ "Cookie": cookie })
            response.raise_for_status()


if __name__ == "__main__":
    main()
