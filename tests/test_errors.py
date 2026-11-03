
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.errors.exceptions import AppException
from shared.errors.handlers import register_error_handlers

app = FastAPI()
register_error_handlers(app)


@app.get("/test-error")
def trigger_test_error():
    raise AppException(
        code="token_expired",
        message="Access token expired",
        status_code=401,
        details={"reason": "expired"},
        retry_after=30
    )


def test_error_status_code():
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/test-error")

    assert response.status_code == 401


def test_standard_error_response():
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/test-error")

    assert response.json() == {
        "error": {
            "code": "token_expired",
            "message": "Access token expired",
            "details": {"reason": "expired"},
            "retry_after": 30
        }
    }

