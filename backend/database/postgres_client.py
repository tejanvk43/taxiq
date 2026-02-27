import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings


def _load_schema_sql() -> str:
    schema_path = Path(__file__).with_name("schema.sql")
    return schema_path.read_text(encoding="utf-8")


class PostgresClient:
    """
    SQLAlchemy engine + session factory.
    If Postgres isn't reachable, callers can catch errors and fall back to in-memory storage.
    """

    def __init__(self, database_url: Optional[str] = None) -> None:
        self.database_url = database_url or settings.DATABASE_URL
        self.engine: Engine = create_engine(self.database_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

    def init_schema(self) -> None:
        schema_sql = _load_schema_sql()
        with self.engine.begin() as conn:
            for stmt in [s.strip() for s in schema_sql.split(";") if s.strip()]:
                conn.execute(text(stmt))
        logger.info("Postgres schema initialized")

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        db = self.SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


postgres_client = PostgresClient()

