
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.errors.exceptions import AppException
from shared.errors.handlers import register_error_handlers


app = FastAPI()
register_error_handlers(app)


ERROR_SCENARIOS = [
    (401, "token_expired"),
    (403, "not_verified"),
    (409, "already_swiped"),
    (429, "quota_exhausted"),
    (451, "region_blocked"),
]


@app.get("/test-scenario/{status_code}/{error_code}")
def trigger_error(status_code: int, error_code: str):
    raise AppException(
        code=error_code,
        message="Test error",
        status_code=status_code,
        retry_after=60 if status_code == 429 else None
    )


@pytest.mark.parametrize("status_code,error_code", ERROR_SCENARIOS)
def test_dating_app_error_scenarios(status_code, error_code):
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        f"/test-scenario/{status_code}/{error_code}"
    )

    assert response.status_code == status_code
    assert response.json()["error"]["code"] == error_code
    assert response.json()["error"]["message"] == "Test error"


def test_quota_exhausted_includes_retry_after():
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        "/test-scenario/429/quota_exhausted"
    )

    assert response.json()["error"]["retry_after"] == 60
