
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from shared.db import Base
from app.models import Profile
from shared.pagination.service import get_profile_page


@pytest.fixture
def db_session():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSession = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    Base.metadata.create_all(test_engine)

    with TestingSession() as session:
        yield session

    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


def add_profiles(db, count=5):
    now = datetime.now(timezone.utc)

    for i in range(count):
        db.add(
            Profile(
                display_name=f"User {i + 1}",
                is_active=True,
                created_at=now - timedelta(minutes=i),
            )
        )

    db.commit()


def test_first_page(db_session):
    add_profiles(db_session, 5)

    result = get_profile_page(
        db=db_session,
        secret="test-secret",
        limit=2,
    )

    assert len(result["items"]) == 2
    assert result["has_more"] is True
    assert result["next_cursor"] is not None


def test_next_page(db_session):
    add_profiles(db_session, 5)

    first_page = get_profile_page(
        db=db_session,
        secret="test-secret",
        limit=2,
    )

    second_page = get_profile_page(
        db=db_session,
        secret="test-secret",
        cursor=first_page["next_cursor"],
        limit=2,
    )

    first_ids = {profile.id for profile in first_page["items"]}
    second_ids = {profile.id for profile in second_page["items"]}

    assert len(second_page["items"]) == 2
    assert first_ids.isdisjoint(second_ids)


def test_inactive_profiles_are_excluded(db_session):
    db_session.add_all([
        Profile(display_name="Active", is_active=True),
        Profile(display_name="Inactive", is_active=False),
    ])
    db_session.commit()

    result = get_profile_page(
        db=db_session,
        secret="test-secret",
    )

    assert all(profile.is_active for profile in result["items"])
    assert len(result["items"]) == 1


def test_invalid_page_limit(db_session):
    with pytest.raises(ValueError):
        get_profile_page(
            db=db_session,
            secret="test-secret",
            limit=0,
        )

def test_default_page_size(db_session):
    add_profiles(db_session, 15)

    result = get_profile_page(
        db=db_session,
        secret="test-secret"
    )

    assert len(result["items"]) == 10
    assert result["has_more"] is True
    assert result["next_cursor"] is not None


def test_maximum_page_size(db_session):
    add_profiles(db_session, 105)

    result = get_profile_page(
        db=db_session,
        secret="test-secret",
        limit=100
    )

    assert len(result["items"]) == 100
    assert result["has_more"] is True


def test_invalid_cursor_is_rejected(db_session):
    from shared.pagination.cursor import InvalidCursor

    with pytest.raises(InvalidCursor):
        get_profile_page(
            db=db_session,
            secret="test-secret",
            cursor="invalid-cursor",
            limit=5
        )


def test_last_page_has_no_next_cursor(db_session):
    add_profiles(db_session, 5)

    first_page = get_profile_page(
        db=db_session,
        secret="test-secret",
        limit=3
    )

    second_page = get_profile_page(
        db=db_session,
        secret="test-secret",
        cursor=first_page["next_cursor"],
        limit=3
    )

    assert len(second_page["items"]) == 2
    assert second_page["has_more"] is False
    assert second_page["next_cursor"] is None
