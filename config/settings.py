"""Environment-based settings for the Academic Audit Analytics Tool.

The module intentionally has no third-party dependencies so it can be imported
by database code, scripts, and tests before the application starts.
"""

from __future__ import annotations

import os
from pathlib import Path


def _read_boolean(name: str, default: bool) -> bool:
    """Read a boolean environment variable or return its default value.

    Accepted true values are ``true``, ``1``, ``yes``, and ``on``. Accepted
    false values are ``false``, ``0``, ``no``, and ``off``.

    Blank or unrecognised values fall back to the supplied default. This keeps
    inherited host environment variables from preventing application startup.
    """
    value = os.getenv(name)
    if value is None or not value.strip():
        return default

    normalized_value = value.strip().lower()
    if normalized_value in {"true", "1", "yes", "on"}:
        return True
    if normalized_value in {"false", "0", "no", "off"}:
        return False

    return default


def _read_path(name: str, default: Path) -> Path:
    """Read a filesystem path from the environment as an expanded ``Path``."""
    return Path(os.getenv(name, str(default))).expanduser()


# The project root is derived from this file, so source checkouts and deployed
# packages can use the same default path layout.
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# APP_ENV differentiates local development defaults from a future production
# deployment. It does not select infrastructure by itself; environment values
# remain the source of truth for paths and URLs.
ENVIRONMENT: str = os.getenv("APP_ENV", "development").strip().lower()

# Store generated SQLite databases under data/ by default. DATA_DIR is created
# eagerly because SQLite cannot create a database file in a missing directory.
DATA_DIR: Path = _read_path("DATA_DIR", PROJECT_ROOT / "data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# DATABASE_PATH is consumed by database.database to construct the SQLite engine.
# Set it to an absolute path in production when the database is on persistent
# storage outside the application release directory.
DATABASE_PATH: Path = _read_path(
    "DATABASE_PATH", DATA_DIR / "academic_audit_analytics.db"
)
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

# DATABASE_URL permits a future non-SQLite deployment to supply a full SQLAlchemy
# URL while retaining a useful SQLite default for local development.
DATABASE_URL: str = os.getenv(
    "DATABASE_URL", f"sqlite:///{DATABASE_PATH.resolve().as_posix()}"
).strip()

# Application metadata is environment-overridable for packaged releases.
APP_NAME: str = os.getenv("APP_NAME", "Academic Audit Analytics Tool").strip()
APP_VERSION: str = os.getenv("APP_VERSION", "0.1.0").strip()

# Development defaults to debug logging; production defaults to standard INFO
# logging unless DEBUG or LOG_LEVEL is explicitly set in the environment.
DEBUG: bool = _read_boolean("DEBUG", default=ENVIRONMENT == "development")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO").upper()

_VALID_LOG_LEVELS: frozenset[str] = frozenset(
    {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}
)
if LOG_LEVEL not in _VALID_LOG_LEVELS:
    raise ValueError(
        "LOG_LEVEL must be one of: " + ", ".join(sorted(_VALID_LOG_LEVELS))
    )
