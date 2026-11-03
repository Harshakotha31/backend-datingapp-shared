
import base64
import hashlib
import hmac
import json

from datetime import datetime, timezone


class InvalidCursor(ValueError):
    """Raised when a pagination cursor is invalid."""
    pass


def _validate_secret(secret: str) -> None:
    if not isinstance(secret, str) or not secret:
        raise ValueError("Cursor secret must not be empty")


def _encode_base64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _decode_base64(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)

    return base64.b64decode(
        data + padding,
        altchars=b"-_",
        validate=True
    )


def encode_cursor(
    created_at: datetime,
    record_id: int,
    secret: str
) -> str:
    """
    Create a signed cursor for descending pagination.
    """

    _validate_secret(secret)

    if not isinstance(created_at, datetime):
        raise ValueError("created_at must be a datetime")

    if not isinstance(record_id, int) or isinstance(record_id, bool):
        raise ValueError("record_id must be an integer")

    if record_id <= 0:
        raise ValueError("record_id must be positive")

    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    created_at = created_at.astimezone(timezone.utc)

    payload = {
        "created_at": created_at.isoformat(),
        "id": record_id
    }

    raw_data = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True
    ).encode("utf-8")

    signature = hmac.new(
        secret.encode("utf-8"),
        raw_data,
        hashlib.sha256
    ).digest()

    return (
        f"{_encode_base64(raw_data)}."
        f"{_encode_base64(signature)}"
    )


def decode_cursor(
    cursor: str,
    secret: str
) -> dict:
    """
    Verify a cursor and return its pagination values.
    """

    _validate_secret(secret)

    try:
        if not isinstance(cursor, str) or not cursor:
            raise InvalidCursor("Cursor is required")

        if len(cursor) > 2048:
            raise InvalidCursor("Cursor is too large")

        parts = cursor.split(".")

        if len(parts) != 2:
            raise InvalidCursor("Invalid cursor format")

        encoded_data, encoded_signature = parts

        raw_data = _decode_base64(encoded_data)
        signature = _decode_base64(encoded_signature)

        expected_signature = hmac.new(
            secret.encode("utf-8"),
            raw_data,
            hashlib.sha256
        ).digest()

        if not hmac.compare_digest(
            signature,
            expected_signature
        ):
            raise InvalidCursor("Invalid cursor signature")

        payload = json.loads(raw_data.decode("utf-8"))

        if not isinstance(payload, dict):
            raise InvalidCursor("Invalid cursor payload")

        if set(payload.keys()) != {"created_at", "id"}:
            raise InvalidCursor("Invalid cursor fields")

        if not isinstance(payload["created_at"], str):
            raise InvalidCursor("Invalid timestamp")

        if (
            not isinstance(payload["id"], int)
            or isinstance(payload["id"], bool)
            or payload["id"] <= 0
        ):
            raise InvalidCursor("Invalid record ID")

        created_at = datetime.fromisoformat(
            payload["created_at"]
        )

        if created_at.tzinfo is None:
            raise InvalidCursor("Cursor timestamp must include timezone")

        return {
            "created_at": created_at,
            "id": payload["id"]
        }

    except InvalidCursor:
        raise

    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        raise InvalidCursor("Invalid cursor") from None

