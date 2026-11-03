# Backend Dating App — Shared Libraries

Reusable backend components developed for the dating application's backend services.

## 1. Features

- **Configuration Management:** Environment-based configuration using Pydantic Settings.
- **Standardized API Errors:** Consistent error response structure using FastAPI exception handlers.
- **HTTP Communication:** Reusable asynchronous HTTP client using HTTPX.
- **Cursor-Based Pagination:** Signed cursor-based pagination using SQLAlchemy.
- **Idempotency Management:** Request deduplication, request hashing, response storage and replay.
- **Database Connection:** PostgreSQL connection management using SQLAlchemy.

## 2. Technology Stack

- Python 3.13+
- FastAPI
- Pydantic Settings
- SQLAlchemy
- PostgreSQL
- HTTPX
- Pytest
- psycopg

## 3. Project Structure

```text
backend-datingapp-shared/
│
├── app/
│   ├── __init__.py
│   └── models.py
│
├── shared/
│   ├── config/
│   │   └── settings.py
│   │
│   ├── errors/
│   │   ├── exceptions.py
│   │   └── handlers.py
│   │
│   ├── http/
│   │   └── client.py
│   │
│   ├── pagination/
│   │   ├── cursor.py
│   │   └── service.py
│   │
│   ├── idempotency/
│   │   ├── models.py
│   │   ├── service.py
│   │   └── store.py
│   │
│   └── db.py
│
├── tests/
│   ├── test_config.py
│   ├── test_cursor.py
│   ├── test_database.py
│   ├── test_errors.py
│   ├── test_error_contract.py
│   ├── test_error_scenarios.py
│   ├── test_http_client.py
│   ├── test_idempotency.py
│   ├── test_idempotency_database.py
│   └── test_pagination.py
│
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

## 4. Installation

Clone the repository and open the project directory.

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## 5. Environment Configuration

Create a `.env` file in the project root.

Example:

```env
APP_NAME=Dating App Backend
ENVIRONMENT=development
PORT=8000
DEBUG=True

DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/dating_app_dev
```

Replace `YOUR_PASSWORD` with your local PostgreSQL password.

**Security:** Never commit `.env` files, database passwords, API keys or other secrets to GitHub.

## 6. Database Configuration

The project uses:

- PostgreSQL as the database.
- SQLAlchemy for database operations.
- psycopg as the PostgreSQL driver.
- SessionLocal for database sessions.
- DeclarativeBase for ORM models.

The database connection is configured in:

```text
shared/db.py
```

## 7. Shared Library Components

### Configuration Management

Location:

```text
shared/config/settings.py
```

Loads application settings and environment variables using Pydantic Settings.

### Standardized Error Handling

Location:

```text
shared/errors/
```

Provides a common API error response format:

```json
{
  "error": {
    "code": "token_expired",
    "message": "Access token expired",
    "details": null,
    "retry_after": null
  }
}
```

### HTTP Client

Location:

```text
shared/http/client.py
```

Supports:
- Asynchronous GET requests.
- Asynchronous POST requests.
- Configurable request timeout.
- HTTP error handling.
- Connection cleanup.
- Async context manager support.

### Cursor-Based Pagination

Location:

```text
shared/pagination/
```

Supports:
- Signed cursor generation.
- Cursor validation.
- Configurable page size.
- Maximum page size.
- Stable ordering using creation timestamp and record ID.
- Next-page retrieval.

### Idempotency Management

Location:

```text
shared/idempotency/
```

Supports:
- Idempotency key validation.
- SHA-256 request hashing.
- Duplicate request detection.
- Request payload conflict detection.
- Response storage and replay.
- Processing request protection.
- Expired record cleanup.

## 8. Running Tests

Run the complete test suite:

```powershell
python -m pytest -p no:cacheprovider -v
```

Run tests for a specific component:

```powershell
python -m pytest -p no:cacheprovider tests/test_http_client.py -v
```

```powershell
python -m pytest -p no:cacheprovider tests/test_pagination.py -v
```

```powershell
python -m pytest -p no:cacheprovider tests/test_idempotency.py tests/test_idempotency_database.py -v
```

### Current Test Results

- Total tests: 49
- Passed: 49
- Failed: 0

These results represent the current local test suite.

## 9. Implementation Scope and Integration Notes

This project is currently a standalone local implementation of reusable backend components.

Before production integration, the implementation requires review against the team's actual repository, API contracts, database schema and deployment conventions.

Additional integration work includes:

- Production database transaction validation.
- Redis-based chat message deduplication using `client_msg_id` and the required 24-hour window.
- Payment webhook integration using PSP event identifiers.
- Authentication and authorization integration.
- Production configuration and secret management.
- Team code review and deployment validation.

## 10. Project Status

Core shared libraries have been implemented and locally tested.

**Current status:** Local implementation and automated testing completed. Team integration and production approval are pending.



