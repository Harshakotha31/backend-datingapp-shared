

import hashlib
import json

from datetime import datetime, timezone

from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from shared.idempotency.models import IdempotencyRecord


# ==========================================
# 1. CUSTOM EXCEPTIONS
# ==========================================

class IdempotencyError(Exception):
    """Base exception for idempotency errors."""
    pass


class IdempotencyKeyConflict(IdempotencyError):
    """Raised when a key is reused with different request data."""
    pass


class IdempotencyRequestInProgress(IdempotencyError):
    """Raised when the original request is still processing."""
    pass


# ==========================================
# 2. IDEMPOTENCY KEY VALIDATION
# ==========================================

def validate_idempotency_key(key: str) -> str:
    """Validate the client-provided idempotency key."""

    if not isinstance(key, str):
        raise ValueError("Idempotency key must be a string")

    key = key.strip()

    if not key:
        raise ValueError("Idempotency key is required")

    if len(key) > 255:
        raise ValueError("Idempotency key is too long")

    return key


# ==========================================
# 3. REQUEST HASH GENERATION
# ==========================================

def generate_request_hash(payload: dict) -> str:
    """Generate a consistent SHA-256 hash from request data."""

    if not isinstance(payload, dict):
        raise ValueError("Request payload must be a dictionary")

    try:
        canonical_payload = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError):
        raise ValueError(
            "Request payload must contain valid JSON data"
        ) from None

    return hashlib.sha256(
        canonical_payload.encode("utf-8")
    ).hexdigest()


# ==========================================
# 4. REQUEST HASH COMPARISON
# ==========================================

def check_request_hash(
    existing_hash: str,
    new_hash: str,
) -> None:
    """Check whether an existing key has the same request payload."""

    if existing_hash != new_hash:
        raise IdempotencyKeyConflict(
            "Idempotency key was already used with different request data"
        )


# ==========================================
# 5. POSTGRESQL KEY RESERVATION
# ==========================================

def reserve_idempotency_key(
    db: Session,
    scope: str,
    key: str,
    payload: dict,
    expires_at: datetime,
) -> tuple[IdempotencyRecord, bool]:
    """
    Atomically reserve an idempotency key.

    Returns:
        (record, True): New key reserved.
        (record, False): Existing key found.

    Caller must commit or roll back the transaction.
    """

    if not isinstance(scope, str) or not scope.strip():
        raise ValueError("Idempotency scope is required")

    scope = scope.strip()
    key = validate_idempotency_key(key)
    request_hash = generate_request_hash(payload)

    if not isinstance(expires_at, datetime):
        raise ValueError("expires_at must be a datetime")

    if expires_at.tzinfo is None:
        raise ValueError("expires_at must include a timezone")

    now = datetime.now(timezone.utc)

    if expires_at <= now:
        raise ValueError("expires_at must be in the future")

    # Allow reuse of expired completed keys.
    db.execute(
        delete(IdempotencyRecord).where(
            IdempotencyRecord.scope == scope,
            IdempotencyRecord.idempotency_key == key,
            IdempotencyRecord.status == "completed",
            IdempotencyRecord.expires_at <= now,
        )
    )

    statement = (
        insert(IdempotencyRecord)
        .values(
            scope=scope,
            idempotency_key=key,
            request_hash=request_hash,
            status="processing",
            expires_at=expires_at,
        )
        .on_conflict_do_nothing(
            constraint="uq_idempotency_scope_key"
        )
        .returning(IdempotencyRecord.id)
    )

    inserted_id = db.execute(
        statement
    ).scalar_one_or_none()

    if inserted_id is not None:
        record = db.get(
            IdempotencyRecord,
            inserted_id,
        )

        if record is None:
            raise RuntimeError("Reserved record was not found")

        return record, True

    existing_record = db.execute(
        select(IdempotencyRecord).where(
            IdempotencyRecord.scope == scope,
            IdempotencyRecord.idempotency_key == key,
        )
    ).scalar_one_or_none()

    if existing_record is None:
        raise RuntimeError("Existing record was not found")

    check_request_hash(
        existing_record.request_hash,
        request_hash,
    )

    return existing_record, False


# ==========================================
# 6. STORE COMPLETED RESPONSE
# ==========================================

def complete_idempotency_request(
    db: Session,
    record_id: int,
    response_status: int,
    response_body: dict | list,
) -> IdempotencyRecord:
    """Store the original HTTP response."""

    if (
        not isinstance(response_status, int)
        or isinstance(response_status, bool)
        or not 100 <= response_status <= 599
    ):
        raise ValueError("Invalid HTTP response status")

    if not isinstance(response_body, (dict, list)):
        raise ValueError("Response body must be a dictionary or list")

    record = db.execute(
        select(IdempotencyRecord)
        .where(IdempotencyRecord.id == record_id)
        .with_for_update()
    ).scalar_one_or_none()

    if record is None:
        raise ValueError("Idempotency record not found")

    if record.status != "processing":
        raise ValueError("Idempotency request is not processing")

    record.status = "completed"
    record.response_status = response_status
    record.response_body = response_body

    db.flush()

    return record


# ==========================================
# 7. REPLAY COMPLETED RESPONSE
# ==========================================

def get_replay_response(
    record: IdempotencyRecord,
) -> dict:
    """Return the saved response for a completed request."""

    if record.status == "processing":
        raise IdempotencyRequestInProgress(
            "The original request is still processing"
        )

    if record.status != "completed":
        raise IdempotencyError(
            "Invalid idempotency record status"
        )

    if record.response_status is None or record.response_body is None:
        raise IdempotencyError(
            "Completed request has no stored response"
        )

    return {
        "status_code": record.response_status,
        "body": record.response_body,
    }


# ==========================================
# 8. EXPIRED RECORD CLEANUP
# ==========================================

def cleanup_expired_idempotency_records(
    db: Session,
    batch_size: int = 500,
) -> int:
    """
    Delete expired completed records in batches.

    Processing records are never deleted by this function.
    Caller must commit the transaction.
    """

    if (
        not isinstance(batch_size, int)
        or isinstance(batch_size, bool)
        or batch_size < 1
        or batch_size > 5000
    ):
        raise ValueError("batch_size must be between 1 and 5000")

    now = datetime.now(timezone.utc)

    expired_ids = (
        select(IdempotencyRecord.id)
        .where(
            IdempotencyRecord.status == "completed",
            IdempotencyRecord.expires_at <= now,
        )
        .order_by(IdempotencyRecord.expires_at.asc())
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )

    result = db.execute(
        delete(IdempotencyRecord).where(
            IdempotencyRecord.id.in_(expired_ids)
        )
    )

    return result.rowcount or 0
