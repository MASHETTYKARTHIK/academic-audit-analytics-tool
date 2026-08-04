"""Framework-independent analytics services for the administrator dashboard."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

from database import queries
from utils.constants import (
    DEFAULT_AT_RISK_THRESHOLD,
    DEFAULT_OUTSTANDING_THRESHOLD,
    DEFAULT_TABLE_LIMIT,
)
from utils.validators import validate_analytics_filters, validate_limit, validate_threshold


FilterValues = Mapping[str, int | None] | queries.AnalyticsFilters | None


@dataclass(frozen=True, slots=True)
class KpiMetrics:
    """Headline metrics for the administrator overview."""

    total_students: int
    total_departments: int
    total_courses: int
    total_faculty: int
    pass_percentage: float
    fail_percentage: float
    average_marks: float
    highest_marks: float
    lowest_marks: float


def _filters(filters: FilterValues) -> queries.AnalyticsFilters:
    """Normalize public service filters for the database query layer."""
    if isinstance(filters, queries.AnalyticsFilters):
        return filters
    return queries.AnalyticsFilters(**validate_analytics_filters(filters))


def _frame(records: list[dict[str, object]]) -> pd.DataFrame:
    """Return a new DataFrame with predictable empty-state behavior."""
    return pd.DataFrame.from_records(records)


def get_kpis(filters: FilterValues = None) -> KpiMetrics:
    """Return the top-level dashboard metrics for the selected scope."""
    scoped_filters = _filters(filters)
    return KpiMetrics(
        total_students=queries.get_total_students(scoped_filters),
        total_departments=queries.get_total_departments(scoped_filters),
        total_courses=queries.get_total_courses(scoped_filters),
        total_faculty=queries.get_total_faculty(scoped_filters),
        pass_percentage=queries.get_pass_percentage(scoped_filters),
        fail_percentage=queries.get_fail_percentage(scoped_filters),
        average_marks=queries.get_average_marks(scoped_filters),
        highest_marks=queries.get_highest_marks(scoped_filters),
        lowest_marks=queries.get_lowest_marks(scoped_filters),
    )


def get_department_analytics(filters: FilterValues = None) -> pd.DataFrame:
    """Return department performance metrics as a DataFrame."""
    return _frame(queries.get_department_wise_results(_filters(filters)))


def get_course_analytics(filters: FilterValues = None) -> pd.DataFrame:
    """Return course performance metrics as a DataFrame."""
    return _frame(queries.get_course_wise_results(_filters(filters)))


def get_faculty_analytics(filters: FilterValues = None) -> pd.DataFrame:
    """Return faculty performance metrics as a DataFrame."""
    return _frame(queries.get_faculty_wise_results(_filters(filters)))


def get_batch_analytics(filters: FilterValues = None) -> pd.DataFrame:
    """Return batch performance metrics as a DataFrame."""
    return _frame(queries.get_batch_wise_results(_filters(filters)))


def get_semester_analytics(filters: FilterValues = None) -> pd.DataFrame:
    """Return semester performance metrics as a DataFrame."""
    return _frame(queries.get_semester_wise_results(_filters(filters)))


def get_grade_distribution(filters: FilterValues = None) -> pd.DataFrame:
    """Return grade counts and percentages as a DataFrame."""
    return _frame(queries.get_grade_distribution(_filters(filters)))


def get_pass_fail_analytics(filters: FilterValues = None) -> pd.DataFrame:
    """Return result-status totals suitable for pass/fail charts."""
    metrics = get_kpis(filters)
    return pd.DataFrame(
        {"result_status": ["Pass", "Fail"], "percentage": [metrics.pass_percentage, metrics.fail_percentage]}
    )


def get_student_performance(
    filters: FilterValues = None,
    at_risk_threshold: float = DEFAULT_AT_RISK_THRESHOLD,
    outstanding_threshold: float = DEFAULT_OUTSTANDING_THRESHOLD,
) -> dict[str, pd.DataFrame]:
    """Return at-risk and outstanding student DataFrames for the selected scope."""
    scoped_filters = _filters(filters)
    return {
        "at_risk": _frame(
            queries.get_students_at_risk(
                scoped_filters, validate_threshold(at_risk_threshold, "at_risk_threshold")
            )
        ),
        "outstanding": _frame(
            queries.get_outstanding_students(
                scoped_filters,
                validate_threshold(outstanding_threshold, "outstanding_threshold"),
            )
        ),
    }


def get_course_rankings(filters: FilterValues = None, limit: int = DEFAULT_TABLE_LIMIT) -> dict[str, pd.DataFrame]:
    """Return top and least performing course rankings."""
    scoped_filters = _filters(filters)
    validated_limit = validate_limit(limit)
    return {
        "top_performing": _frame(queries.get_top_performing_courses(scoped_filters, validated_limit)),
        "least_performing": _frame(queries.get_least_performing_courses(scoped_filters, validated_limit)),
    }
