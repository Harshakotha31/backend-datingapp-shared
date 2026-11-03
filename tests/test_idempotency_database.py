
from datetime import datetime, timedelta, timezone

import pytest
from shared.idempotency.service import (
    get_replay_response,
    IdempotencyRequestInProgress,
)
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from shared.db import SessionLocal

from shared.idempotency.service import (
    get_replay_response,
)
from shared.db import SessionLocal, Base, engine
from shared.idempotency.models import IdempotencyRecord
from shared.idempotency.service import (
    reserve_idempotency_key,
    IdempotencyKeyConflict,
)
from shared.idempotency.service import (
    cleanup_expired_idempotency_records,
)


@pytest.fixture
def db():
    Base.metadata.create_all(engine)

    with SessionLocal() as session:
        yield session
        session.rollback()

    # Remove only test records.
    with SessionLocal() as session:
        session.query(IdempotencyRecord).filter(
            IdempotencyRecord.scope == "test-like-user-1"
        ).delete()
        session.commit()


def test_new_key_is_reserved(db):
    record, created = reserve_idempotency_key(
        db=db,
        scope="test-like-user-1",
        key="like-test-001",
        payload={"target_id": 10, "action": "like"},
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )

    assert created is True
    assert record.status == "processing"

    db.commit()


def test_duplicate_key_returns_existing_record(db):
    expiry = datetime.now(timezone.utc) + timedelta(hours=24)

    first, created_first = reserve_idempotency_key(
        db=db,
        scope="test-like-user-1",
        key="like-test-002",
        payload={"target_id": 20, "action": "like"},
        expires_at=expiry,
    )

    db.commit()

    second, created_second = reserve_idempotency_key(
        db=db,
        scope="test-like-user-1",
        key="like-test-002",
        payload={"target_id": 20, "action": "like"},
        expires_at=expiry,
    )

    assert created_first is True
    assert created_second is False
    assert first.id == second.id

    db.commit()


def test_same_key_different_payload_is_rejected(db):
    expiry = datetime.now(timezone.utc) + timedelta(hours=24)

    reserve_idempotency_key(
        db=db,
        scope="test-like-user-1",
        key="like-test-003",
        payload={"target_id": 30, "action": "like"},
        expires_at=expiry,
    )

    db.commit()

    with pytest.raises(IdempotencyKeyConflict):
        reserve_idempotency_key(
            db=db,
            scope="test-like-user-1",
            key="like-test-003",
            payload={"target_id": 40, "action": "like"},
            expires_at=expiry,
        )

from shared.idempotency.service import complete_idempotency_request


def test_completed_response_is_saved(db):
    record, created = reserve_idempotency_key(
        db=db,
        scope="test-like-user-1",
        key="like-test-004",
        payload={"target_id": 50, "action": "like"},
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )

    assert created is True

    completed = complete_idempotency_request(
        db=db,
        record_id=record.id,
        response_status=201,
        response_body={
            "message": "Like created",
            "target_id": 50,
        },
    )

    db.commit()
    db.refresh(completed)

    assert completed.status == "completed"
    assert completed.response_status == 201
    assert completed.response_body["target_id"] == 50


def test_duplicate_request_replays_saved_response(db):
    expiry = datetime.now(timezone.utc) + timedelta(hours=24)

    record, created = reserve_idempotency_key(
        db=db,
        scope="test-like-user-1",
        key="like-test-005",
        payload={"target_id": 60, "action": "like"},
        expires_at=expiry,
    )

    assert created is True

    complete_idempotency_request(
        db=db,
        record_id=record.id,
        response_status=201,
        response_body={
            "message": "Like created",
            "target_id": 60,
        },
    )

    db.commit()

    duplicate, created_again = reserve_idempotency_key(
        db=db,
        scope="test-like-user-1",
        key="like-test-005",
        payload={"target_id": 60, "action": "like"},
        expires_at=expiry,
    )

    assert created_again is False

    replay = get_replay_response(duplicate)

    assert replay["status_code"] == 201
    assert replay["body"]["target_id"] == 60


def test_processing_request_cannot_be_replayed(db):
    record, created = reserve_idempotency_key(
        db=db,
        scope="test-like-user-1",
        key="like-test-006",
        payload={"target_id": 70, "action": "like"},
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )

    assert created is True

    with pytest.raises(IdempotencyRequestInProgress):
        get_replay_response(record)

    db.commit()


def test_concurrent_requests_use_one_reservation(db):
    first_reserved = Event()
    second_attempting = Event()
    allow_first_commit = Event()

    scope = "test-like-user-1"
    key = "like-concurrent-001"
    payload = {
        "target_id": 80,
        "action": "like",
    }

    expiry = datetime.now(timezone.utc) + timedelta(hours=24)

    def first_request():
        with SessionLocal() as session:
            record, created = reserve_idempotency_key(
                db=session,
                scope=scope,
                key=key,
                payload=payload,
                expires_at=expiry,
            )

            first_reserved.set()

            if not allow_first_commit.wait(timeout=15):
                raise TimeoutError("First transaction was not released")

            complete_idempotency_request(
                db=session,
                record_id=record.id,
                response_status=201,
                response_body={
                    "message": "Like created",
                    "target_id": 80,
                },
            )

            session.commit()

            return created, record.id

    def second_request():
        if not first_reserved.wait(timeout=15):
            raise TimeoutError("First reservation was not created")

        with SessionLocal() as session:
            second_attempting.set()

            record, created = reserve_idempotency_key(
                db=session,
                scope=scope,
                key=key,
                payload=payload,
                expires_at=expiry,
            )

            replay = None

            if not created:
                replay = get_replay_response(record)

            session.commit()

            return created, record.id, replay

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(first_request)

        assert first_reserved.wait(timeout=15)

        second_future = executor.submit(second_request)

        assert second_attempting.wait(timeout=15)

        # Allow the first transaction to complete.
        allow_first_commit.set()

        first_created, first_id = first_future.result(timeout=20)

        second_created, second_id, replay = second_future.result(
            timeout=20
        )

    assert first_created is True
    assert second_created is False
    assert first_id == second_id

    assert replay["status_code"] == 201
    assert replay["body"]["target_id"] == 80


def test_expired_completed_key_can_be_reused(db):
    old_expiry = datetime.now(timezone.utc) + timedelta(seconds=1)

    record, created = reserve_idempotency_key(
        db=db,
        scope="test-like-user-1",
        key="like-expired-001",
        payload={"target_id": 90, "action": "like"},
        expires_at=old_expiry,
    )

    complete_idempotency_request(
        db=db,
        record_id=record.id,
        response_status=201,
        response_body={"message": "Like created"},
    )

    db.commit()

    # Move expiry into the past for a deterministic test.
    record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    new_record, created_again = reserve_idempotency_key(
        db=db,
        scope="test-like-user-1",
        key="like-expired-001",
        payload={"target_id": 91, "action": "like"},
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )

    assert created_again is True
    assert new_record.id != record.id

    db.commit()


def test_cleanup_removes_expired_completed_records(db):
    record, created = reserve_idempotency_key(
        db=db,
        scope="test-like-user-1",
        key="like-cleanup-001",
        payload={"target_id": 100, "action": "like"},
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )

    complete_idempotency_request(
        db=db,
        record_id=record.id,
        response_status=201,
        response_body={"message": "Like created"},
    )

    db.commit()

    record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    deleted_count = cleanup_expired_idempotency_records(db)

    db.commit()

    assert deleted_count >= 1
    assert db.get(IdempotencyRecord, record.id) is None
