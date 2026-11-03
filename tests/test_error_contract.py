
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.errors.exceptions import AppException
from shared.errors.handlers import register_error_handlers


def create_test_app():
    app = FastAPI()

    register_error_handlers(app)

    @app.get("/test-error")
    async def test_error():
        raise AppException(
            code="token_expired",
            message="Your session has expired",
            status_code=401,
            details={"reason": "expired"},
            retry_after=30
        )

    return app


def test_error_response_contract():
    app = create_test_app()
    client = TestClient(app)

    response = client.get("/test-error")

    assert response.status_code == 401

    assert response.json() == {
        "error": {
            "code": "token_expired",
            "message": "Your session has expired",
            "details": {"reason": "expired"},
            "retry_after": 30
        }
    }
