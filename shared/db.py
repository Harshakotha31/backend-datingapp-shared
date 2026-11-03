import os

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    sessionmaker
)

# Load environment variables
load_dotenv()

# Read database URL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not configured"
    )

# Create database engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Create database sessions
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False
)


# Base class for database models
class Base(DeclarativeBase):
    pass


# FastAPI database dependency
def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()