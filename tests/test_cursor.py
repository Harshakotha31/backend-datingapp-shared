from datetime import datetime, timezone

import pytest

from shared.pagination.cursor import (
    encode_cursor,
    decode_cursor,
    InvalidCursor
)


def test_cursor_encoding_and_decoding():

    created_at = datetime(
        2026, 11, 4,
        tzinfo=timezone.utc
    )

    cursor = encode_cursor(
        created_at,
        100,
        "test-secret"
    )

    result = decode_cursor(
        cursor,
        "test-secret"
    )

    assert result["id"] == 100
    assert result["created_at"] == created_at


def test_invalid_cursor_secret():

    created_at = datetime.now(timezone.utc)

    cursor = encode_cursor(
        created_at,
        100,
        "secret-one"
    )

    with pytest.raises(InvalidCursor):

        decode_cursor(
            cursor,
            "secret-two"
        )