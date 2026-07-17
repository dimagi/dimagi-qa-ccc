import pytest

from utils.helpers import ConfigLoader, SettingsLoader, TestDataLoader


def pytest_addoption(parser):
    parser.addoption(
        "--env",
        action="store",
        default="stage",
        help="Environment to run tests against: prod or stage (defaults to stage)",
    )


@pytest.fixture(scope="session")
def config(request):
    return ConfigLoader(request.config.getoption("--env"))


@pytest.fixture(scope="session")
def settings():
    return SettingsLoader()


@pytest.fixture(scope="session")
def test_data():
    return TestDataLoader()
