from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from app.core.config import get_settings

settings = get_settings()

engine_args = {
    "pool_pre_ping": True,
    "echo": False,
}
if "postgresql" in settings.database_url:
    engine_args["connect_args"] = {"connect_timeout": 2}
    engine_args["pool_size"] = 10
    engine_args["max_overflow"] = 20

engine = create_engine(settings.database_url, **engine_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Session:
    """Dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
