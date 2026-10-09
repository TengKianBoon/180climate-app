import pytest

@pytest.fixture(autouse=True)
def offline_screening_fixtures(monkeypatch):
    monkeypatch.setenv("SCREENING_USE_TEST_FIXTURES", "true")
