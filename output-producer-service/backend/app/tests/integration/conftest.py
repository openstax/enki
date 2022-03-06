import pytest


@pytest.fixture(scope="module")
def api_url():
    return "http://backend/api"
