from datetime import datetime

from sqlalchemy import (
    Integer,
    String,
    Boolean,
    DateTime,
    Index,
    func
)

from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base


class Profile(Base):

    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )


Index(
    "ix_profiles_active_created_id",
    Profile.is_active,
    Profile.created_at.desc(),
    Profile.id.desc()
)
