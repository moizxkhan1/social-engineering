from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


_engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {},
)

SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def init_db() -> None:
    # Ensure models are registered before create_all.
    from .. import models  # noqa: F401

    Base.metadata.create_all(bind=_engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
