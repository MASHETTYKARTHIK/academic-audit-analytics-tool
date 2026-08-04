"""Application-level configuration derived from :mod:`config.settings`.

This module collects presentation and runtime settings that other application
layers can consume without reading environment variables directly.  Environment
parsing remains exclusively in ``config.settings``.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from config import settings


@dataclass(frozen=True, slots=True)
class ApplicationConfig:
    """Immutable runtime configuration for the administrator application."""

    app_name: str
    app_version: str
    environment: str
    debug: bool
    log_level: str
    project_root: Path
    data_dir: Path
    database_path: Path
    database_url: str
    page_title: str
    page_icon: str
    layout: str
    initial_sidebar_state: str


@lru_cache(maxsize=1)
def get_application_config() -> ApplicationConfig:
    """Return the cached application configuration derived from settings."""
    return ApplicationConfig(
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
        log_level=settings.LOG_LEVEL,
        project_root=settings.PROJECT_ROOT,
        data_dir=settings.DATA_DIR,
        database_path=settings.DATABASE_PATH,
        database_url=settings.DATABASE_URL,
        page_title=settings.APP_NAME,
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

