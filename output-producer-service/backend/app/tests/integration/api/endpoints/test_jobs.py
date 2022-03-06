import json

import pytest
import requests

ENDPOINT = "jobs"


# FIXME: Database should be populated with test data.
@pytest.mark.integration
@pytest.mark.nondestructive
def test_jobs_get_request(api_url):
    # GIVEN: An api url to the jobs endpoint
    url = f"{api_url}/{ENDPOINT}"

    # WHEN: A GET request is made to the url
    response = requests.get(url)

    # THEN: A proper response is returned
    assert response.json() == []


@pytest.mark.integration
def test_jobs_post_request_successful(api_url):
    # GIVEN: An api url to the jobs endpoint
    # AND: Data for job is ready to be submitted.
    url = f"{api_url}/{ENDPOINT}"
    data = {
        "collection_id": "abc123",
        "status_id": "1",
        "content_server_id": "1",
        "job_type_id": "1"
    }

    # WHEN: A POST request is made to the url with data
    response = requests.post(url, data=json.dumps(data))

    # THEN: A 200 code is returned
    # AND: Correct attributes of the request exist in the response
    assert response.status_code == 200

    response = response.json()

    assert response["collection_id"] == "abc123"
    assert response["content_server"]["hostname"] == "content01.cnx.org"
    assert response["status"]["name"] == "queued"
    assert response["job_type"]["name"] == "pdf"

