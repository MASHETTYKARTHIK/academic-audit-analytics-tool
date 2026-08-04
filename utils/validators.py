"""Input validation helpers shared by services and future UI components."""

from __future__ import annotations

from collections.abc import Mapping
from numbers import Integral, Real

from utils.constants import ANALYTICS_FILTER_FIELDS, MAX_TABLE_LIMIT


class ValidationError(ValueError):
    """Raised when supplied application input fails validation."""


def validate_identifier(value: int | None, field_name: str) -> int | None:
    """Validate an optional positive database identifier."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, Integral) or value < 1:
        raise ValidationError(f"{field_name} must be a positive integer or None")
    return int(value)


def validate_analytics_filters(filters: Mapping[str, int | None] | None) -> dict[str, int | None]:
    """Validate supported analytics filters and return a normalized copy."""
    if filters is None:
        return {}

    invalid_fields = set(filters).difference(ANALYTICS_FILTER_FIELDS)
    if invalid_fields:
        names = ", ".join(sorted(invalid_fields))
        raise ValidationError(f"Unsupported analytics filter(s): {names}")

    return {
        field_name: validate_identifier(value, field_name)
        for field_name, value in filters.items()
        if value is not None
    }


def validate_threshold(value: float, field_name: str = "threshold") -> float:
    """Validate a percentage threshold in the inclusive range 0 through 100."""
    if isinstance(value, bool) or not isinstance(value, Real) or not 0 <= value <= 100:
        raise ValidationError(f"{field_name} must be between 0 and 100")
    return float(value)


def validate_limit(value: int, maximum: int = MAX_TABLE_LIMIT) -> int:
    """Validate a positive presentation limit against a safe maximum."""
    if isinstance(value, bool) or not isinstance(value, Integral) or not 1 <= value <= maximum:
        raise ValidationError(f"limit must be between 1 and {maximum}")
    return int(value)


def validate_required_text(value: str, field_name: str, maximum_length: int = 255) -> str:
    """Return trimmed text after validating that it is present and bounded."""
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be text")
    normalized_value = value.strip()
    if not normalized_value:
        raise ValidationError(f"{field_name} is required")
    if len(normalized_value) > maximum_length:
        raise ValidationError(f"{field_name} must not exceed {maximum_length} characters")
    return normalized_value
