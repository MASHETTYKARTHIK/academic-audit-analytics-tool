"""Reusable, parameterized SQL queries for administrator-level analytics."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from typing import Any, TypeAlias

from database.database import execute_query


@dataclass(frozen=True, slots=True)
class AnalyticsFilters:
    """Optional dimension filters shared by all analytics query functions."""

    academic_year_id: int | None = None
    department_id: int | None = None
    program_id: int | None = None
    batch_id: int | None = None
    semester_id: int | None = None
    section_id: int | None = None
    course_id: int | None = None
    faculty_id: int | None = None


FilterInput: TypeAlias = AnalyticsFilters | Mapping[str, int | None] | None

_FILTER_COLUMNS = {
    "academic_year_id": "academic_year.academic_year_id",
    "department_id": "department.department_id",
    "program_id": "program.program_id",
    "batch_id": "batch.batch_id",
    "semester_id": "semester.semester_id",
    "section_id": "section.section_id",
    "course_id": "course.course_id",
    "faculty_id": "faculty.faculty_id",
}

_RESULTS_FROM = """
    FROM marks
    JOIN enrollments AS enrollment ON enrollment.enrollment_id = marks.enrollment_id
    JOIN students AS student ON student.student_id = enrollment.student_id
    JOIN batches AS batch ON batch.batch_id = student.batch_id
    JOIN programs AS program ON program.program_id = batch.program_id
    JOIN departments AS department ON department.department_id = program.department_id
    JOIN course_offerings AS offering ON offering.offering_id = enrollment.offering_id
    JOIN courses AS course ON course.course_id = offering.course_id
    JOIN semesters AS semester ON semester.semester_id = offering.semester_id
    JOIN academic_years AS academic_year
        ON academic_year.academic_year_id = semester.academic_year_id
    JOIN sections AS section ON section.section_id = offering.section_id
    JOIN faculty ON faculty.faculty_id = offering.faculty_id
"""


def _normalize_filters(filters: FilterInput) -> AnalyticsFilters:
    """Convert a filter mapping to the typed immutable filter object."""
    if filters is None:
        return AnalyticsFilters()
    if isinstance(filters, AnalyticsFilters):
        return filters

    valid_names = {field.name for field in fields(AnalyticsFilters)}
    invalid_names = set(filters) - valid_names
    if invalid_names:
        names = ", ".join(sorted(invalid_names))
        raise ValueError(f"Unsupported analytics filter(s): {names}")

    return AnalyticsFilters(**dict(filters))


def _where_clause(filters: FilterInput, include_completed_results: bool = True) -> str:
    """Build a safe WHERE clause from fixed columns and named parameters."""
    normalized_filters = _normalize_filters(filters)
    conditions: list[str] = []

    if include_completed_results:
        conditions.append("marks.result_status IN ('Pass', 'Fail')")

    for field_name, column_name in _FILTER_COLUMNS.items():
        value = getattr(normalized_filters, field_name)
        if value is not None:
            conditions.append(f"{column_name} = :{field_name}")

    return f"WHERE {' AND '.join(conditions)}" if conditions else ""


def _parameters(filters: FilterInput, **additional: Any) -> dict[str, Any]:
    """Return values for a query's named parameters."""
    normalized_filters = _normalize_filters(filters)
    parameters = {
        field.name: getattr(normalized_filters, field.name)
        for field in fields(AnalyticsFilters)
        if getattr(normalized_filters, field.name) is not None
    }
    parameters.update(additional)
    return parameters


def _result_cte(filters: FilterInput) -> str:
    """Return the common, filtered result-record CTE used by mark analytics."""
    return f"""
        WITH filtered_results AS (
            SELECT marks.*, student.student_id, student.student_number,
                   student.first_name, student.last_name,
                   department.department_id, department.department_code,
                   department.department_name, program.program_id,
                   program.program_code, program.program_name, batch.batch_id,
                   batch.batch_label, course.course_id, course.course_code,
                   course.course_title, semester.semester_id,
                   semester.semester_number, semester.semester_name,
                   academic_year.academic_year_id, academic_year.year_label,
                   section.section_id, section.section_name, faculty.faculty_id,
                   faculty.employee_number, faculty.first_name AS faculty_first_name,
                   faculty.last_name AS faculty_last_name
            {_RESULTS_FROM}
            {_where_clause(filters)}
        )
    """


def _scalar(query: str, filters: FilterInput, key: str) -> float | int:
    """Execute a scalar query and convert a null aggregate to zero."""
    rows = execute_query(query, _parameters(filters))
    value = rows[0][key] if rows else 0
    return 0 if value is None else value


def _bounded_limit(limit: int) -> int:
    """Validate a presentation limit before it is supplied to SQLite."""
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    return limit


def get_total_students(filters: FilterInput = None) -> int:
    """Return distinct students represented by the filtered published results."""
    query = f"""
        {_result_cte(filters)}
        SELECT COUNT(DISTINCT student_id) AS total_students
        FROM filtered_results
    """
    return int(_scalar(query, filters, "total_students"))


def get_total_departments(filters: FilterInput = None) -> int:
    """Return departments represented by the filtered published results."""
    query = f"""
        {_result_cte(filters)}
        SELECT COUNT(DISTINCT department_id) AS total_departments
        FROM filtered_results
    """
    return int(_scalar(query, filters, "total_departments"))


def get_total_courses(filters: FilterInput = None) -> int:
    """Return courses represented by the filtered published results."""
    query = f"""
        {_result_cte(filters)}
        SELECT COUNT(DISTINCT course_id) AS total_courses
        FROM filtered_results
    """
    return int(_scalar(query, filters, "total_courses"))


def get_total_faculty(filters: FilterInput = None) -> int:
    """Return faculty members represented by filtered published results."""
    query = f"""
        {_result_cte(filters)}
        SELECT COUNT(DISTINCT faculty_id) AS total_faculty
        FROM filtered_results
    """
    return int(_scalar(query, filters, "total_faculty"))


def get_students_passed(filters: FilterInput = None) -> int:
    """Return distinct students with at least one passing filtered result."""
    query = f"""
        {_result_cte(filters)}
        SELECT COUNT(DISTINCT student_id) AS students_passed
        FROM filtered_results
        WHERE result_status = 'Pass'
    """
    return int(_scalar(query, filters, "students_passed"))


def get_students_failed(filters: FilterInput = None) -> int:
    """Return distinct students with at least one failing filtered result."""
    query = f"""
        {_result_cte(filters)}
        SELECT COUNT(DISTINCT student_id) AS students_failed
        FROM filtered_results
        WHERE result_status = 'Fail'
    """
    return int(_scalar(query, filters, "students_failed"))


def get_pass_percentage(filters: FilterInput = None) -> float:
    """Return the percentage of completed result records that passed."""
    query = f"""
        {_result_cte(filters)}
        SELECT COALESCE(
            ROUND(100.0 * SUM(result_status = 'Pass') / NULLIF(COUNT(*), 0), 2), 0
        ) AS pass_percentage
        FROM filtered_results
    """
    return float(_scalar(query, filters, "pass_percentage"))


def get_fail_percentage(filters: FilterInput = None) -> float:
    """Return the percentage of completed result records that failed."""
    query = f"""
        {_result_cte(filters)}
        SELECT COALESCE(
            ROUND(100.0 * SUM(result_status = 'Fail') / NULLIF(COUNT(*), 0), 2), 0
        ) AS fail_percentage
        FROM filtered_results
    """
    return float(_scalar(query, filters, "fail_percentage"))


def get_average_marks(filters: FilterInput = None) -> float:
    """Return average total marks for completed result records."""
    query = f"""
        {_result_cte(filters)}
        SELECT COALESCE(ROUND(AVG(total_marks), 2), 0) AS average_marks
        FROM filtered_results
    """
    return float(_scalar(query, filters, "average_marks"))


def get_highest_marks(filters: FilterInput = None) -> float:
    """Return the highest total mark in the filtered result scope."""
    query = f"""
        {_result_cte(filters)}
        SELECT COALESCE(MAX(total_marks), 0) AS highest_marks
        FROM filtered_results
    """
    return float(_scalar(query, filters, "highest_marks"))


def get_lowest_marks(filters: FilterInput = None) -> float:
    """Return the lowest total mark in the filtered result scope."""
    query = f"""
        {_result_cte(filters)}
        SELECT COALESCE(MIN(total_marks), 0) AS lowest_marks
        FROM filtered_results
    """
    return float(_scalar(query, filters, "lowest_marks"))


def get_median_marks(filters: FilterInput = None) -> float:
    """Return the median mark using SQLite window functions."""
    query = f"""
        {_result_cte(filters)},
        ranked_results AS (
            SELECT total_marks,
                   ROW_NUMBER() OVER (ORDER BY total_marks) AS row_number,
                   COUNT(*) OVER () AS result_count
            FROM filtered_results
        )
        SELECT COALESCE(ROUND(AVG(total_marks), 2), 0) AS median_marks
        FROM ranked_results
        WHERE row_number IN ((result_count + 1) / 2, (result_count + 2) / 2)
    """
    return float(_scalar(query, filters, "median_marks"))


def _grouped_results(
    filters: FilterInput,
    group_columns: str,
    order_by: str,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Return standard pass/fail metrics grouped by one or more dimensions."""
    limit_sql = "LIMIT :limit" if limit is not None else ""
    query = f"""
        {_result_cte(filters)}
        SELECT {group_columns},
               COUNT(*) AS total_results,
               SUM(result_status = 'Pass') AS passed_results,
               SUM(result_status = 'Fail') AS failed_results,
               ROUND(100.0 * SUM(result_status = 'Pass') / COUNT(*), 2)
                   AS pass_percentage,
               ROUND(AVG(total_marks), 2) AS average_marks,
               MAX(total_marks) AS highest_marks,
               MIN(total_marks) AS lowest_marks
        FROM filtered_results
        GROUP BY {group_columns}
        ORDER BY {order_by}
        {limit_sql}
    """
    parameters = _parameters(filters)
    if limit is not None:
        parameters["limit"] = _bounded_limit(limit)
    return execute_query(query, parameters)


def get_department_wise_results(filters: FilterInput = None) -> list[dict[str, Any]]:
    """Return aggregate outcomes for each department."""
    return _grouped_results(
        filters,
        "department_id, department_code, department_name",
        "pass_percentage DESC, department_name",
    )


def get_course_wise_results(filters: FilterInput = None) -> list[dict[str, Any]]:
    """Return aggregate outcomes for each course."""
    return _grouped_results(
        filters,
        "course_id, course_code, course_title",
        "pass_percentage DESC, course_code",
    )


def get_semester_wise_results(filters: FilterInput = None) -> list[dict[str, Any]]:
    """Return aggregate outcomes for each semester."""
    return _grouped_results(
        filters,
        "semester_id, year_label, semester_number, semester_name",
        "year_label, semester_number",
    )


def get_faculty_wise_results(filters: FilterInput = None) -> list[dict[str, Any]]:
    """Return aggregate outcomes for each faculty member."""
    return _grouped_results(
        filters,
        "faculty_id, employee_number, faculty_first_name, faculty_last_name",
        "pass_percentage DESC, faculty_last_name, faculty_first_name",
    )


def get_batch_wise_results(filters: FilterInput = None) -> list[dict[str, Any]]:
    """Return aggregate outcomes for each student batch."""
    return _grouped_results(
        filters,
        "batch_id, batch_label, program_code, program_name",
        "pass_percentage DESC, batch_label",
    )


def get_section_wise_results(filters: FilterInput = None) -> list[dict[str, Any]]:
    """Return aggregate outcomes for each teaching section."""
    return _grouped_results(
        filters,
        "section_id, section_name, batch_label, program_code",
        "pass_percentage DESC, batch_label, section_name",
    )


def get_top_performing_courses(
    filters: FilterInput = None, limit: int = 10
) -> list[dict[str, Any]]:
    """Return courses ordered from highest to lowest pass percentage."""
    return _grouped_results(
        filters,
        "course_id, course_code, course_title",
        "pass_percentage DESC, average_marks DESC, course_code",
        limit,
    )


def get_least_performing_courses(
    filters: FilterInput = None, limit: int = 10
) -> list[dict[str, Any]]:
    """Return courses ordered from lowest to highest pass percentage."""
    return _grouped_results(
        filters,
        "course_id, course_code, course_title",
        "pass_percentage ASC, average_marks ASC, course_code",
        limit,
    )


def get_grade_distribution(filters: FilterInput = None) -> list[dict[str, Any]]:
    """Return counts and percentages for each grade in the result scope."""
    query = f"""
        {_result_cte(filters)}
        SELECT grade,
               COUNT(*) AS student_count,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS percentage
        FROM filtered_results
        GROUP BY grade
        ORDER BY CASE grade
            WHEN 'O' THEN 1 WHEN 'A+' THEN 2 WHEN 'A' THEN 3
            WHEN 'B+' THEN 4 WHEN 'B' THEN 5 WHEN 'C' THEN 6
            WHEN 'P' THEN 7 WHEN 'F' THEN 8 ELSE 9
        END
    """
    return execute_query(query, _parameters(filters))


def get_students_at_risk(
    filters: FilterInput = None, threshold: float = 50.0
) -> list[dict[str, Any]]:
    """Return students with a failed result or average below ``threshold``."""
    if not 0 <= threshold <= 100:
        raise ValueError("threshold must be between 0 and 100")

    query = f"""
        {_result_cte(filters)}
        SELECT student_id, student_number, first_name, last_name,
               department_name, program_name, batch_label,
               COUNT(*) AS total_results,
               SUM(result_status = 'Fail') AS failed_results,
               ROUND(AVG(total_marks), 2) AS average_marks
        FROM filtered_results
        GROUP BY student_id, student_number, first_name, last_name,
                 department_name, program_name, batch_label
        HAVING SUM(result_status = 'Fail') > 0 OR AVG(total_marks) < :threshold
        ORDER BY failed_results DESC, average_marks ASC, student_number
    """
    return execute_query(query, _parameters(filters, threshold=threshold))


def get_outstanding_students(
    filters: FilterInput = None, threshold: float = 85.0
) -> list[dict[str, Any]]:
    """Return students meeting the excellence threshold with no failures."""
    if not 0 <= threshold <= 100:
        raise ValueError("threshold must be between 0 and 100")

    query = f"""
        {_result_cte(filters)}
        SELECT student_id, student_number, first_name, last_name,
               department_name, program_name, batch_label,
               COUNT(*) AS total_results,
               ROUND(AVG(total_marks), 2) AS average_marks,
               MAX(total_marks) AS highest_marks
        FROM filtered_results
        GROUP BY student_id, student_number, first_name, last_name,
                 department_name, program_name, batch_label
        HAVING SUM(result_status = 'Fail') = 0 AND AVG(total_marks) >= :threshold
        ORDER BY average_marks DESC, highest_marks DESC, student_number
    """
    return execute_query(query, _parameters(filters, threshold=threshold))
