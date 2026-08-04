"""Streamlit administrator dashboard UI for academic audit analytics."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

from analytics import admin_analytics, visualizations
from config.config import get_application_config
from database.database import execute_query
from modules.reports import build_excel_report, build_pdf_report
from utils.constants import FILTER_LABELS
from utils.logger import get_logger

LOGGER = get_logger(__name__)


def _inject_styles() -> None:
    """Apply dashboard-only dark glassmorphism styles."""
    st.markdown(
        """
        <style>
        .stApp { background: radial-gradient(circle at top right, #172554, #0b1120 48%); }
        .block-container { max-width: 1800px; padding-top: 1.35rem; padding-bottom: 2rem; }
        [data-testid="stSidebar"] { min-width: 320px; max-width: 320px; background: rgba(15, 23, 42, .96); border-right: 1px solid #263247; }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: .65rem; padding-top: .5rem; }
        [data-testid="stSidebarCollapseButton"] { display: none; }
        [data-testid="stSidebar"] button { min-height: 2.65rem; text-align: left; padding-inline: .85rem; }
        [data-testid="stSidebar"] button:disabled { opacity: .62; color: #94a3b8; border-color: #334155; }
        .dashboard-title { font-size: clamp(2rem, 3vw, 2.7rem); font-weight: 750; color: #f8fafc; margin: 0; letter-spacing: -.04em; }
        .dashboard-subtitle { color: #94a3b8; font-size: 1.04rem; margin-top: .35rem; }
        .dashboard-meta { color: #cbd5e1; font-size: .9rem; min-width: 220px; min-height: 112px; box-sizing: border-box; padding: 1rem 1.15rem; line-height: 1.55; border: 1px solid rgba(148,163,184,.16); border-radius: 14px; background: rgba(23,32,51,.58); }
        .dashboard-meta-label { color: #94a3b8; font-size: .73rem; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; }
        [data-testid="stSelectbox"] label { color: #cbd5e1; font-size: .84rem; }
        .section-title { color: #f8fafc; font-weight: 700; font-size: 1.35rem; margin: 1.25rem 0 .4rem; }
        .insight-card { background: rgba(23, 32, 51, .72); border: 1px solid rgba(148,163,184,.18);
            border-radius: 16px; padding: 1.1rem 1.15rem; min-height: 98px; color: #dbeafe; }
        .insight-card strong { color: #60a5fa; display: block; margin-bottom: .35rem; font-size: .96rem; }
        [data-testid="stPlotlyChart"] { background: rgba(17, 24, 39, .45); border: 1px solid rgba(148,163,184,.12);
            border-radius: 16px; padding: .3rem; box-shadow: 0 14px 30px rgba(0,0,0,.14); }
        .stButton > button { border-radius: 10px; border: 1px solid #334155; background: #172033; color: #e5e7eb; }
        [data-testid="stDataFrame"] { border: 1px solid rgba(148,163,184,.16); border-radius: 12px; overflow: hidden; }
        @media (max-width: 900px) {
            .block-container { padding-left: 1rem; padding-right: 1rem; }
            .dashboard-meta { min-width: 0; margin-top: .65rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _lookup_options(query: str, filters: dict[str, int | None]) -> list[dict[str, Any]]:
    """Return filter option records through the existing database access API."""
    return execute_query(query, filters)


def _select_filter(
    container: Any, label: str, records: list[dict[str, Any]], key: str
) -> int | None:
    """Render a select box with a consistent ``All`` option."""
    values = [None, *[int(record["id"]) for record in records]]
    labels = {
        None: "All",
        **{int(record["id"]): str(record["label"]) for record in records},
    }
    if st.session_state.get(key) not in values:
        st.session_state[key] = None
    return container.selectbox(label, values, format_func=labels.get, key=key)


def _analytics_options(
    frame: pd.DataFrame, identifier: str, label: str
) -> list[dict[str, Any]]:
    """Build display options only from result-backed analytic records."""
    if frame.empty or identifier not in frame or label not in frame:
        return []
    return [
        {"id": int(record[identifier]), "label": str(record[label])}
        for record in frame[[identifier, label]].drop_duplicates().to_dict("records")
    ]


def _reset_dependents_on_change(
    key: str, selected_value: int | None, dependents: tuple[str, ...]
) -> None:
    """Clear stale child selections whenever an upstream scope changes."""
    previous_value_key = f"_{key}_previous_value"
    if (
        previous_value_key in st.session_state
        and st.session_state[previous_value_key] != selected_value
    ):
        for dependent in dependents:
            st.session_state[dependent] = None
    st.session_state[previous_value_key] = selected_value


def _render_filters() -> dict[str, int | None]:
    """Render cascading administrator filters and return their selected IDs."""
    st.markdown(
        f'<p class="section-title">{"Analytics Filters"}</p>',
        unsafe_allow_html=True,
    )
    filter_columns = [*st.columns(4), *st.columns(4)]
    filters: dict[str, int | None] = {}
    filters["academic_year_id"] = _select_filter(
        filter_columns[0],
        FILTER_LABELS["academic_year_id"],
        _lookup_options(
            "SELECT academic_year_id AS id, year_label AS label FROM academic_years ORDER BY year_label DESC",
            filters,
        ),
        "audit_year",
    )
    _reset_dependents_on_change(
        "audit_year",
        filters["academic_year_id"],
        ("audit_semester", "audit_course", "audit_faculty"),
    )
    filters["department_id"] = _select_filter(
        filter_columns[1],
        FILTER_LABELS["department_id"],
        _lookup_options(
            "SELECT department_id AS id, department_name AS label FROM departments ORDER BY department_name",
            filters,
        ),
        "audit_department",
    )
    _reset_dependents_on_change(
        "audit_department",
        filters["department_id"],
        (
            "audit_program",
            "audit_batch",
            "audit_section",
            "audit_course",
            "audit_faculty",
        ),
    )
    filters["program_id"] = _select_filter(
        filter_columns[2],
        FILTER_LABELS["program_id"],
        _lookup_options(
            "SELECT program_id AS id, program_name AS label FROM programs WHERE (:department_id IS NULL OR department_id = :department_id) ORDER BY program_name",
            filters,
        ),
        "audit_program",
    )
    _reset_dependents_on_change(
        "audit_program",
        filters["program_id"],
        ("audit_batch", "audit_section", "audit_course", "audit_faculty"),
    )
    filters["batch_id"] = _select_filter(
        filter_columns[3],
        FILTER_LABELS["batch_id"],
        _analytics_options(
            admin_analytics.get_batch_analytics(filters), "batch_id", "batch_label"
        ),
        "audit_batch",
    )
    _reset_dependents_on_change(
        "audit_batch",
        filters["batch_id"],
        ("audit_section", "audit_course", "audit_faculty"),
    )
    filters["semester_id"] = _select_filter(
        filter_columns[4],
        FILTER_LABELS["semester_id"],
        _lookup_options(
            "SELECT semester_id AS id, semester_name || ' (' || semester_number || ')' AS label FROM semesters WHERE (:academic_year_id IS NULL OR academic_year_id = :academic_year_id) ORDER BY semester_number",
            filters,
        ),
        "audit_semester",
    )
    _reset_dependents_on_change(
        "audit_semester",
        filters["semester_id"],
        ("audit_course", "audit_faculty"),
    )
    filters["section_id"] = _select_filter(
        filter_columns[5],
        FILTER_LABELS["section_id"],
        (
            _lookup_options(
                "SELECT section_id AS id, section_name AS label FROM sections WHERE (:batch_id IS NULL OR batch_id = :batch_id) ORDER BY section_name",
                filters,
            )
            if filters["batch_id"] is not None
            or (filters["department_id"] is None and filters["program_id"] is None)
            else []
        ),
        "audit_section",
    )
    _reset_dependents_on_change(
        "audit_section",
        filters["section_id"],
        ("audit_course", "audit_faculty"),
    )
    filters["course_id"] = _select_filter(
        filter_columns[6],
        FILTER_LABELS["course_id"],
        _analytics_options(
            admin_analytics.get_course_analytics(filters),
            "course_id",
            "course_title",
        ),
        "audit_course",
    )
    _reset_dependents_on_change(
        "audit_course", filters["course_id"], ("audit_faculty",)
    )
    filters["faculty_id"] = _select_filter(
        filter_columns[7],
        FILTER_LABELS["faculty_id"],
        _analytics_options(
            admin_analytics.get_faculty_analytics(filters),
            "faculty_id",
            "employee_number",
        ),
        "audit_faculty",
    )
    return filters


@st.fragment(run_every="1s")
def _render_header_metadata(version: str) -> None:
    """Render self-updating runtime details without rerunning dashboard analytics."""
    now = datetime.now().astimezone()
    st.markdown(
        "<div class='dashboard-meta'>"
        f"<span class='dashboard-meta-label'>📅 Current Date</span><br>{now:%d %b %Y}<br>"
        f"<span class='dashboard-meta-label'>🕒 Current Time</span><br>{now:%H:%M:%S %Z}<br>"
        f"<span class='dashboard-meta-label'>⟳ Last Refreshed</span><br>{now:%d %b %Y<br>%I:%M:%S %p}<br>"
        f"<span class='dashboard-meta-label'>ℹ Version</span><br>{version}"
        "</div>",
        unsafe_allow_html=True,
    )


def _render_header() -> None:
    """Render the dashboard identity and responsive administrator info panel."""
    config = get_application_config()
    left, metadata = st.columns([2.4, 1.6], vertical_alignment="center")
    with left:
        st.markdown(
            '<p class="dashboard-title">Academic Audit Analytics Tool</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p class="dashboard-subtitle">University Academic Audit Analytics Dashboard</p>',
            unsafe_allow_html=True,
        )
    with metadata:
        _render_header_metadata(config.app_version)


def _render_kpis(metrics: admin_analytics.KpiMetrics) -> None:
    """Render the primary KPI indicator row with reusable visualization cards."""
    cards = [
        (
            "👥 Total Students",
            metrics.total_students,
            "",
            "Active student records",
        ),
        (
            "🏛️ Departments",
            metrics.total_departments,
            "",
            "In selected scope",
        ),
        (
            "📚 Courses",
            metrics.total_courses,
            "",
            "Published course results",
        ),
        (
            "👩‍🏫 Faculty",
            metrics.total_faculty,
            "",
            "Teaching faculty represented",
        ),
        (
            "📈 Average Marks",
            metrics.average_marks,
            "",
            "Across completed results",
        ),
        (
            "🏆 Highest Marks",
            metrics.highest_marks,
            "",
            "Top result recorded",
        ),
        (
            "📉 Lowest Marks",
            metrics.lowest_marks,
            "",
            "Lowest result recorded",
        ),
        (
            "✓ Pass Percentage",
            metrics.pass_percentage,
            "%",
            "Completed results passing",
        ),
        (
            "⚠ Fail Percentage",
            metrics.fail_percentage,
            "%",
            "Completed results failing",
        ),
    ]
    for start in range(0, len(cards), 3):
        columns = st.columns(3)
        for column, (label, value, suffix, subtitle) in zip(
            columns, cards[start : start + 3]
        ):
            with column:
                st.plotly_chart(
                    visualizations.create_kpi_card(
                        label, value, suffix=suffix, subtitle=subtitle
                    ),
                    width="stretch",
                    config=visualizations.get_export_config(
                        label.lower().replace(" ", "-")
                    ),
                )


def _render_chart(
    container: Any, figure_factory: Callable[[], Any], filename: str
) -> None:
    """Render one chart safely without preventing the rest of the dashboard."""
    try:
        container.plotly_chart(
            figure_factory(),
            width="stretch",
            config=visualizations.get_export_config(filename),
        )
    except Exception:
        LOGGER.exception("Unable to render chart '%s'.", filename)
        container.info("This visualization is temporarily unavailable.")


def _student_table_config() -> dict[str, Any]:
    """Return presentation-only column labels and widths for intervention tables."""
    return {
        "student_id": None,
        "student_number": st.column_config.TextColumn("Student ID", width="medium"),
        "first_name": st.column_config.TextColumn("First Name", width="small"),
        "last_name": st.column_config.TextColumn("Last Name", width="small"),
        "department_name": st.column_config.TextColumn("Department", width="medium"),
        "program_name": st.column_config.TextColumn("Program", width="medium"),
        "batch_label": st.column_config.TextColumn("Batch", width="small"),
        "total_results": st.column_config.NumberColumn("Results", format="%d"),
        "failed_results": st.column_config.NumberColumn("Failed", format="%d"),
        "average_marks": st.column_config.NumberColumn("Average Marks", format="%.2f"),
    }


def _render_insights(
    departments: pd.DataFrame,
    courses: pd.DataFrame,
    metrics: admin_analytics.KpiMetrics,
) -> None:
    """Generate administrator-facing insights from the displayed aggregates."""
    st.markdown(
        f'<p class="section-title">{"Executive Insights"}</p>',
        unsafe_allow_html=True,
    )
    insights: list[tuple[str, str, str]] = [
        (
            "📊",
            "University Performance",
            "<b>"
            + f"{metrics.average_marks:.2f} average marks with a {metrics.pass_percentage:.2f}% pass rate."
            + "</b>",
        )
    ]
    if not departments.empty:
        best, worst = departments.iloc[0], departments.iloc[-1]
        insights.extend(
            [
                (
                    "🏆",
                    "Highest Performing Department",
                    "{department} leads at {pass_rate:.2f}%.".format(
                        department=best["department_name"],
                        pass_rate=best["pass_percentage"],
                    ),
                ),
                (
                    "⚠️",
                    "Department Requiring Attention",
                    "{department} is at {pass_rate:.2f}%.".format(
                        department=worst["department_name"],
                        pass_rate=worst["pass_percentage"],
                    ),
                ),
            ]
        )
    if not courses.empty:
        difficult = courses.sort_values("pass_percentage").iloc[0]
        insights.append(
            (
                "📘",
                "Most Difficult Course",
                "{course} has a {pass_rate:.2f}% pass rate.".format(
                    course=difficult["course_title"],
                    pass_rate=difficult["pass_percentage"],
                ),
            )
        )
    columns = st.columns(len(insights))
    for column, (icon, heading, content) in zip(columns, insights):
        column.markdown(
            f'<div class="insight-card"><strong>{icon} {heading}</strong>{content}</div>',
            unsafe_allow_html=True,
        )


def render_administrator_dashboard() -> None:
    """Render the complete administrator-only academic audit dashboard."""
    _inject_styles()
    _render_header()
    filters = _render_filters()
    metrics = admin_analytics.get_kpis(filters)
    _render_kpis(metrics)
    departments, courses = (
        admin_analytics.get_department_analytics(filters),
        admin_analytics.get_course_analytics(filters),
    )
    faculty, semesters = (
        admin_analytics.get_faculty_analytics(filters),
        admin_analytics.get_semester_analytics(filters),
    )
    batches, grades = (
        admin_analytics.get_batch_analytics(filters),
        admin_analytics.get_grade_distribution(filters),
    )
    rankings, students = (
        admin_analytics.get_course_rankings(filters),
        admin_analytics.get_student_performance(filters),
    )
    st.markdown(
        f'<p class="section-title">{"Performance Analytics"}</p>',
        unsafe_allow_html=True,
    )
    row_one, row_two = st.columns(2)
    _render_chart(
        row_one,
        lambda: visualizations.create_bar_chart(
            departments,
            "department_name",
            "pass_percentage",
            "Department Performance",
        ),
        "department-performance",
    )
    _render_chart(
        row_two,
        lambda: visualizations.create_horizontal_bar_chart(
            courses, "course_title", "pass_percentage", "Course Performance"
        ),
        "course-performance",
    )
    row_three, row_four = st.columns(2)
    _render_chart(
        row_three,
        lambda: visualizations.create_bar_chart(
            faculty, "employee_number", "pass_percentage", "Faculty Performance"
        ),
        "faculty-performance",
    )
    _render_chart(
        row_four,
        lambda: visualizations.create_line_chart(
            semesters, "semester_name", "pass_percentage", "Semester Performance"
        ),
        "semester-performance",
    )
    row_five, row_six = st.columns(2)
    _render_chart(
        row_five,
        lambda: visualizations.create_bar_chart(
            batches, "batch_label", "pass_percentage", "Batch Performance"
        ),
        "batch-performance",
    )
    _render_chart(
        row_six,
        lambda: visualizations.create_donut_chart(
            admin_analytics.get_pass_fail_analytics(filters),
            "result_status",
            "percentage",
            "Pass vs Fail",
        ),
        "pass-fail",
    )
    row_seven, row_eight = st.columns(2)
    _render_chart(
        row_seven,
        lambda: visualizations.create_donut_chart(
            grades, "grade", "student_count", "Grade Distribution"
        ),
        "grade-distribution",
    )
    _render_chart(
        row_eight,
        lambda: visualizations.create_comparison_chart(
            departments,
            "department_name",
            ["pass_percentage", "average_marks"],
            "Department Comparison",
        ),
        "department-comparison",
    )
    top_courses, least_courses = st.columns(2)
    _render_chart(
        top_courses,
        lambda: visualizations.create_horizontal_bar_chart(
            rankings["top_performing"],
            "course_title",
            "pass_percentage",
            "Top Performing Courses",
        ),
        "top-courses",
    )
    _render_chart(
        least_courses,
        lambda: visualizations.create_horizontal_bar_chart(
            rankings["least_performing"],
            "course_title",
            "pass_percentage",
            "Least Performing Courses",
        ),
        "least-courses",
    )
    _render_insights(departments, courses, metrics)
    st.markdown(
        '<p class="section-title">Student Intervention</p>', unsafe_allow_html=True
    )
    st.subheader("Students at Risk")
    st.caption("Students below the intervention threshold, ordered by average marks.")
    if students["at_risk"].empty:
        st.info("No students at risk found for the selected filters.")
    else:
        st.dataframe(
            students["at_risk"],
            use_container_width=True,
            height=360,
            hide_index=True,
            column_config=_student_table_config(),
        )
    st.divider()
    st.subheader("Outstanding Students")
    if students["outstanding"].empty:
        st.info("No outstanding students found for the selected filters.")
    else:
        st.dataframe(
            students["outstanding"],
            use_container_width=True,
            height=360,
            hide_index=True,
            column_config=_student_table_config(),
        )
    st.markdown('<p class="section-title">Reports</p>', unsafe_allow_html=True)
    report_frames = {
        "departments": departments,
        "courses": courses,
        "faculty": faculty,
        "at_risk": students["at_risk"],
        "outstanding": students["outstanding"],
    }
    has_report_data = any(not frame.empty for frame in report_frames.values())
    report_kpis = {
        "Total Students": metrics.total_students,
        "Departments": metrics.total_departments,
        "Courses": metrics.total_courses,
        "Faculty": metrics.total_faculty,
        "Average Marks": metrics.average_marks,
        "Pass Percentage": f"{metrics.pass_percentage}%",
    }
    report_filters = {
        label: str(filters.get(field) or "All")
        for field, label in FILTER_LABELS.items()
    }
    report_time = datetime.now().astimezone()
    report_columns = st.columns(2)
    report_columns[0].download_button(
        "📄 Export PDF",
        data=build_pdf_report(
            report_time.strftime("%d %b %Y %I:%M:%S %p"),
            report_filters,
            report_kpis,
            report_frames,
            ["University performance summary generated from selected filters."],
        )
        if has_report_data
        else b"",
        file_name=report_time.strftime("Academic_Audit_Report_%Y%m%d_%H%M.pdf"),
        mime="application/pdf",
        disabled=not has_report_data,
        width="stretch",
    )
    report_columns[1].download_button(
        "📊 Export Excel",
        data=build_excel_report(report_filters, report_kpis, report_frames)
        if has_report_data
        else b"",
        file_name="Academic_Audit_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=not has_report_data,
        width="stretch",
    )
