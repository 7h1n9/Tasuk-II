from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def ensure_compatibility_schema() -> None:
    """Apply the small forward-compatible additions used by live local databases."""
    inspector = inspect(engine)
    if not inspector.has_table("challenge_instances"):
        return
    columns = {column["name"] for column in inspector.get_columns("challenge_instances")}
    if "variant_seed" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE challenge_instances ADD COLUMN variant_seed VARCHAR(128) NOT NULL DEFAULT ''"))
