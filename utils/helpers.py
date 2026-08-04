"""Small reusable, framework-independent helper functions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from numbers import Number
from typing import Any, TypeVar


Record = Mapping[str, Any]
T = TypeVar("T")


def safe_divide(numerator: Number, denominator: Number, default: float = 0.0) -> float:
    """Return a division result, or ``default`` when the denominator is zero."""
    if denominator == 0:
        return default
    return float(numerator / denominator)


def format_number(value: Number | None, decimal_places: int = 0) -> str:
    """Format a numeric value for a compact dashboard label."""
    if value is None:
        return "—"
    if decimal_places < 0:
        raise ValueError("decimal_places must be zero or greater")
    return f"{value:,.{decimal_places}f}"


def format_percentage(value: Number | None, decimal_places: int = 2) -> str:
    """Format a numeric percentage value with a percent sign."""
    return f"{format_number(value, decimal_places)}%" if value is not None else "—"


def format_marks(value: Number | None, decimal_places: int = 2) -> str:
    """Format a mark value for consistent display across analytics views."""
    return format_number(value, decimal_places)


def display_name(first_name: str | None, last_name: str | None) -> str:
    """Return a normalized full name without introducing extra spaces."""
    name_parts = [part.strip() for part in (first_name, last_name) if part and part.strip()]
    return " ".join(name_parts) or "Unknown"


def records_to_options(
    records: Sequence[Record],
    value_key: str,
    label_key: str,
    all_label: str = "All",
) -> list[tuple[Any | None, str]]:
    """Convert query records into ordered value/label options for any UI layer."""
    options: list[tuple[Any | None, str]] = [(None, all_label)]
    options.extend((record[value_key], str(record[label_key])) for record in records)
    return options


def compact_records(records: Sequence[Record], keys: Sequence[str]) -> list[dict[str, Any]]:
    """Return copies containing only selected keys from each source record."""
    return [{key: record.get(key) for key in keys} for record in records]

