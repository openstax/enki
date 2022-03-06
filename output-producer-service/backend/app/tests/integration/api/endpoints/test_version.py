import pytest
import requests

ENDPOINT = "version"


@pytest.mark.integration
@pytest.mark.nondestructive
def test_version_get_request(api_url):
    # GIVEN: An api url to the version endpoint
    url = f"{api_url}/{ENDPOINT}"

    # WHEN: A GET request is made to the url
    response = requests.get(url)

    # THEN: A proper response is returned
    assert response.json() == {"stack_name": "dev",
                               "revision": "dev",
                               "tag": "dev",
                               "deployed_at": "20210101.111111"
                               }
