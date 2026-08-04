"""Shared immutable values used by analytics and presentation layers."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final


ANALYTICS_FILTER_FIELDS: Final[tuple[str, ...]] = (
    "academic_year_id",
    "department_id",
    "program_id",
    "batch_id",
    "semester_id",
    "section_id",
    "course_id",
    "faculty_id",
)

FILTER_LABELS: Final = MappingProxyType(
    {
        "academic_year_id": "Academic Year",
        "department_id": "Department",
        "program_id": "Program",
        "batch_id": "Batch",
        "semester_id": "Semester",
        "section_id": "Section",
        "course_id": "Course",
        "faculty_id": "Faculty",
    }
)

GRADE_ORDER: Final[tuple[str, ...]] = ("O", "A+", "A", "B+", "B", "C", "P", "F", "I")
PASS_GRADE_ORDER: Final[tuple[str, ...]] = GRADE_ORDER[:-2]

DEFAULT_AT_RISK_THRESHOLD: Final[float] = 50.0
DEFAULT_OUTSTANDING_THRESHOLD: Final[float] = 85.0
DEFAULT_TABLE_LIMIT: Final[int] = 10
MAX_TABLE_LIMIT: Final[int] = 100

CHART_COLORS: Final = MappingProxyType(
    {
        "primary": "#6C63FF",
        "secondary": "#00C2A8",
        "success": "#22C55E",
        "warning": "#F59E0B",
        "danger": "#EF4444",
        "info": "#38BDF8",
        "muted": "#94A3B8",
    }
)

RESULT_STATUS_COLORS: Final = MappingProxyType(
    {"Pass": CHART_COLORS["success"], "Fail": CHART_COLORS["danger"], "Incomplete": CHART_COLORS["warning"]}
)

