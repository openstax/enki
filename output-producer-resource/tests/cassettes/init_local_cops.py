"""This is a utility script used to initialize a local COPS environment for
recording vcr cassettes. See README.md for use of this script.
"""

import requests

API_ROOT = "http://localhost/api"


def main():
    url = f"{API_ROOT}/jobs"

    data = {
        "collection_id": "col12345",
        "status_id": "",
        "content_server_id": "1",
        "style": "book_style",
        "job_type_id": ""
    }

    # Generate various permutations of job types and states
    for status_id in ["1", "2", "3", "4", "5"]:
        for job_type_id in ["1", "2"]:
            data["status_id"] = status_id
            data["job_type_id"] = job_type_id

            response = requests.post(url, json=data)
            response.raise_for_status()


if __name__ == "__main__":
    main()
