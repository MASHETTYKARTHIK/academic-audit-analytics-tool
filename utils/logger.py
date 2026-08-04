"""Consistent logging setup for the Academic Audit Analytics Tool."""

from __future__ import annotations

import logging
from typing import Final

from config.config import get_application_config


LOG_FORMAT: Final[str] = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
_HANDLER_MARKER: Final[str] = "academic_audit_console_handler"


def configure_logging() -> logging.Logger:
    """Configure process logging once and return the application logger.

    Streamlit reruns application scripts, so the function marks its console
    handler and avoids creating duplicate log entries on subsequent calls.
    """
    application_config = get_application_config()
    root_logger = logging.getLogger()
    root_logger.setLevel(application_config.log_level)

    if not any(
        getattr(handler, "_academic_audit_handler", False)
        for handler in root_logger.handlers
    ):
        console_handler = logging.StreamHandler()
        console_handler._academic_audit_handler = True  # type: ignore[attr-defined]
        console_handler.set_name(_HANDLER_MARKER)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        root_logger.addHandler(console_handler)

    application_logger = logging.getLogger("academic_audit")
    application_logger.setLevel(application_config.log_level)
    return application_logger


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for an application module.

    Args:
        name: Usually the caller's ``__name__`` value.
    """
    configure_logging()
    return logging.getLogger(name)

