import os


def pytest_addoption(parser):
    group = parser.getgroup("selenium", "selenium")
    group.addoption(
        "--disable-dev-shm-usage",
        action="store_true",
        default=os.getenv("DISABLE_DEV_SHM_USAGE", False),
        help="disable chrome's usage of /dev/shm. (used by Travis)",
    )
    group.addoption(
        "--headless",
        action="store_true",
        default=os.getenv("HEADLESS", False),
        help="enable headless mode for chrome. So chrome does not interrupt you.",
    )
    group.addoption(
        "--no-sandbox",
        action="store_true",
        default=os.getenv("NO_SANDBOX", False),
        help="disable chrome's sandbox. (used by Travis)",
    )


def get_custom_markers():
    """Function used to register custom markers.

    Define custom markers within this function to register them in pytest
    """
    return (
        "integration: mark tests that are integration tests",
        "smoke: mark tests used for smoke testing",
        "ui: mark tests used for ui tests",
    )


def pytest_configure(config):
    for marker in get_custom_markers():
        config.addinivalue_line("markers", marker)
