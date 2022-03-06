import pytest
import requests

ENDPOINT = "ping"

@pytest.mark.integration
@pytest.mark.nondestructive
def test_ping_get_request(api_url):
    # GIVEN: An api url to the ping endpoint
    url = f"{api_url}/{ENDPOINT}"

    # WHEN: A GET request is made to the url
    response = requests.get(url)

    # THEN: A proper response is returned
    assert response.json() == {'message': 'pong'}
