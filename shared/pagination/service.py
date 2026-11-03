
from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from app.models import Profile
from shared.pagination.cursor import (
    encode_cursor,
    decode_cursor,
    InvalidCursor,
)


DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100


def get_profile_page(
    db: Session,
    secret: str,
    cursor: str | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
) -> dict:
    """
    Retrieve active profiles using cursor-based pagination.

    Profiles are ordered by created_at DESC, then id DESC.
    """

    if not isinstance(limit, int) or isinstance(limit, bool):
        raise ValueError("Limit must be an integer")

    if limit < 1 or limit > MAX_PAGE_SIZE:
        raise ValueError(
            f"Limit must be between 1 and {MAX_PAGE_SIZE}"
        )

    statement = select(Profile).where(
        Profile.is_active.is_(True)
    )

    if cursor:
        cursor_data = decode_cursor(cursor, secret)

        statement = statement.where(
            tuple_(Profile.created_at, Profile.id)
            < tuple_(
                cursor_data["created_at"],
                cursor_data["id"]
            )
        )

    statement = (
        statement
        .order_by(
            Profile.created_at.desc(),
            Profile.id.desc()
        )
        .limit(limit + 1)
    )

    profiles = list(db.scalars(statement).all())

    has_more = len(profiles) > limit

    if has_more:
        profiles = profiles[:limit]

    next_cursor = None

    if has_more and profiles:
        last_profile = profiles[-1]

        next_cursor = encode_cursor(
            created_at=last_profile.created_at,
            record_id=last_profile.id,
            secret=secret
        )

    return {
        "items": profiles,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }
