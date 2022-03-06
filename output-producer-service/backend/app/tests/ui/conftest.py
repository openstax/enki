import os

import pytest
from chromedriver_binary import add_chromedriver_to_path


@pytest.fixture
def language(request):
    return "en"


@pytest.fixture
def chrome_options(chrome_options, pytestconfig, language):
    if pytestconfig.getoption("--headless"):
        chrome_options.headless = True

    # Required to run in Travis containers
    if pytestconfig.getoption("--no-sandbox"):
        chrome_options.add_argument("--no-sandbox")
    if pytestconfig.getoption("--disable-dev-shm-usage"):
        chrome_options.add_argument("--disable-dev-shm-usage")

    # Set the browser language
    chrome_options.add_argument("--lang={lang}".format(lang=language))
    chrome_options.add_experimental_option("prefs", {"intl.accept_languages": language})
    chrome_options.add_experimental_option("w3c", False)

    return chrome_options


