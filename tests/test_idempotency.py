
import pytest

from shared.idempotency.service import (
    validate_idempotency_key,
    generate_request_hash,
    check_request_hash,
    IdempotencyKeyConflict,
)


def test_valid_idempotency_key():
    assert validate_idempotency_key("request-123") == "request-123"


def test_empty_idempotency_key():
    with pytest.raises(ValueError):
        validate_idempotency_key("")


def test_request_hash_is_consistent():
    first = generate_request_hash({
        "target_id": 10,
        "action": "like",
    })

    second = generate_request_hash({
        "action": "like",
        "target_id": 10,
    })

    assert first == second


def test_different_payloads_have_different_hashes():
    first = generate_request_hash({"target_id": 10})
    second = generate_request_hash({"target_id": 20})

    assert first != second


def test_same_request_hash_is_accepted():
    check_request_hash("abc123", "abc123")


def test_different_request_hash_is_rejected():
    with pytest.raises(IdempotencyKeyConflict):
        check_request_hash("abc123", "xyz789")

def test_idempotency_key_maximum_length():
    key = "a" * 255

    assert validate_idempotency_key(key) == key


def test_idempotency_key_too_long():
    key = "a" * 256

    with pytest.raises(ValueError):
        validate_idempotency_key(key)


def test_idempotency_key_wrong_type():
    with pytest.raises(ValueError):
        validate_idempotency_key(123)
