"""Reusable SQLAlchemy database access for the academic audit application.

The module owns one process-wide SQLAlchemy engine.  Callers receive short-lived
sessions from that engine through :func:`get_session` and should use it as a
context manager.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Any

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import Result
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql import Executable

from config import settings


LOGGER = logging.getLogger(__name__)

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None
_engine_lock = RLock()


class DatabaseConfigurationError(RuntimeError):
    """Raised when the required database configuration is unavailable."""


def _get_database_path() -> Path:
    """Return the configured SQLite database path.

    ``DATABASE_PATH`` belongs in ``config/settings.py`` so deployments can set
    their own location without requiring database code changes.

    Raises:
        DatabaseConfigurationError: If ``settings.DATABASE_PATH`` is missing
            or blank.
    """
    configured_path = getattr(settings, "DATABASE_PATH", None)
    if configured_path is None or not str(configured_path).strip():
        message = (
            "config.settings.DATABASE_PATH must be set before the database "
            "can be initialized."
        )
        LOGGER.error(message)
        raise DatabaseConfigurationError(message)

    return Path(configured_path).expanduser()


def _enable_sqlite_foreign_keys(
    dbapi_connection: sqlite3.Connection, connection_record: Any
) -> None:
    """Enable SQLite foreign-key enforcement for every pooled connection."""
    del connection_record
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys = ON")
    finally:
        cursor.close()


def get_engine() -> Engine:
    """Return the singleton SQLAlchemy engine for the configured SQLite file.

    The parent directory is created on first use, allowing a configured path
    such as ``data/academic_audit.db`` to work in a fresh checkout.
    """
    global _engine

    if _engine is not None:
        return _engine

    with _engine_lock:
        if _engine is None:
            database_path = _get_database_path().resolve()
            database_path.parent.mkdir(parents=True, exist_ok=True)
            database_url = f"sqlite:///{database_path.as_posix()}"

            try:
                _engine = create_engine(
                    database_url,
                    future=True,
                    connect_args={"check_same_thread": False},
                )
                event.listen(_engine, "connect", _enable_sqlite_foreign_keys)
                LOGGER.info("Created database engine for %s", database_path)
            except SQLAlchemyError as error:
                LOGGER.exception("Unable to create the database engine.")
                raise RuntimeError("Unable to create the database engine.") from error

    return _engine


def _get_session_factory() -> sessionmaker[Session]:
    """Return the singleton factory that creates isolated ORM sessions."""
    global _session_factory

    if _session_factory is None:
        with _engine_lock:
            if _session_factory is None:
                _session_factory = sessionmaker(
                    bind=get_engine(),
                    autoflush=False,
                    expire_on_commit=False,
                )

    return _session_factory


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Yield a transaction-scoped session, committing or rolling back safely."""
    session = _get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        LOGGER.exception("Database session failed and was rolled back.")
        raise
    finally:
        session.close()


def initialize_database() -> None:
    """Create all schema objects defined by ``database/schema.sql``.

    The schema uses ``CREATE ... IF NOT EXISTS`` statements, so this operation
    is safe to call when the database was initialized previously.
    """
    schema_path = Path(__file__).with_name("schema.sql")
    try:
        schema_sql = schema_path.read_text(encoding="utf-8")
    except OSError as error:
        LOGGER.exception("Unable to read database schema from %s", schema_path)
        raise RuntimeError("Unable to read the database schema.") from error

    try:
        raw_connection = get_engine().raw_connection()
        try:
            raw_connection.executescript(schema_sql)
            raw_connection.commit()
        finally:
            raw_connection.close()
        LOGGER.info("Database schema initialized successfully.")
    except (SQLAlchemyError, sqlite3.Error) as error:
        LOGGER.exception("Unable to initialize the database schema.")
        raise RuntimeError("Unable to initialize the database schema.") from error


def execute_query(
    query: str | Executable,
    parameters: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Execute a parameterized SQL statement and return any result rows.

    Args:
        query: SQL text or a SQLAlchemy executable statement.  Use named
            parameters for dynamic values, never string interpolation.
        parameters: Values keyed by the query's named parameters.

    Returns:
        A list of dictionary rows for result-producing statements; an empty
        list for statements that do not return rows.
    """
    statement = text(query) if isinstance(query, str) else query
    query_parameters = dict(parameters or {})

    try:
        with get_engine().begin() as connection:
            result: Result[Any] = connection.execute(statement, query_parameters)
            if result.returns_rows:
                return [dict(row) for row in result.mappings().all()]
            return []
    except SQLAlchemyError:
        LOGGER.exception("Database query execution failed.")
        raise
