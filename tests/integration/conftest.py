import pytest

from nolito.client import NolioApiClient


@pytest.fixture(scope="session")
def client() -> NolioApiClient:
    return NolioApiClient()
