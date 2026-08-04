"""Administrator dashboard report exports without changing analytics behavior."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _frame_rows(frame: pd.DataFrame, limit: int = 12) -> list[list[str]]:
    """Return a compact string table safe for report output."""
    if frame.empty:
        return [["No data available for the selected filters."]]
    return [
        [str(value) for value in row]
        for row in frame.head(limit).itertuples(index=False, name=None)
    ]


def _pdf_table(title: str, frame: pd.DataFrame, styles: Any) -> list[Any]:
    """Create a readable bounded-width PDF table section."""
    rows = _frame_rows(frame)
    header = list(frame.columns) if not frame.empty else ["Status"]
    table = Table([header, *rows], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#172033")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F8FAFC")],
                ),
            ]
        )
    )
    return [Paragraph(title, styles["Heading3"]), table, Spacer(1, 0.35 * cm)]


def build_pdf_report(
    generated_at: str,
    filters: dict[str, str],
    kpis: dict[str, Any],
    frames: dict[str, pd.DataFrame],
    insights: list[str],
) -> bytes:
    """Build a professional PDF summary from existing dashboard data."""
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=28,
        leftMargin=28,
        topMargin=28,
        bottomMargin=28,
    )
    styles = getSampleStyleSheet()
    story: list[Any] = [
        Paragraph("Academic Audit Analytics Tool", styles["Title"]),
        Paragraph("University Name Placeholder", styles["Heading2"]),
        Paragraph(f"Generated: {generated_at}", styles["Normal"]),
        Spacer(1, 0.35 * cm),
        Paragraph("Selected Filters", styles["Heading2"]),
        Table(
            [[name, value] for name, value in filters.items()]
            or [["Scope", "All records"]]
        ),
        Spacer(1, 0.35 * cm),
        Paragraph("KPI Summary", styles["Heading2"]),
        Table([[name, str(value)] for name, value in kpis.items()]),
        Spacer(1, 0.35 * cm),
        Paragraph("Executive Insights", styles["Heading2"]),
    ]
    story.extend(Paragraph(item, styles["BodyText"]) for item in insights)
    story.append(Spacer(1, 0.25 * cm))
    for title, key in (
        ("Department Summary", "departments"),
        ("Course Summary", "courses"),
        ("Faculty Summary", "faculty"),
        ("Students At Risk", "at_risk"),
        ("Outstanding Students", "outstanding"),
    ):
        story.extend(_pdf_table(title, frames[key], styles))
    document.build(story)
    return output.getvalue()


def build_excel_report(
    filters: dict[str, str], kpis: dict[str, Any], frames: dict[str, pd.DataFrame]
) -> bytes:
    """Build a multi-sheet workbook containing existing dashboard data."""
    workbook = Workbook()
    workbook.remove(workbook.active)
    sheets: list[tuple[str, pd.DataFrame]] = [
        ("Dashboard Summary", pd.DataFrame(kpis.items(), columns=["Metric", "Value"])),
        ("Department Performance", frames["departments"]),
        ("Course Performance", frames["courses"]),
        ("Faculty Performance", frames["faculty"]),
        ("Students At Risk", frames["at_risk"]),
        ("Outstanding Students", frames["outstanding"]),
        (
            "Selected Filters",
            pd.DataFrame(filters.items(), columns=["Filter", "Selection"]),
        ),
    ]
    for name, frame in sheets:
        worksheet = workbook.create_sheet(name)
        for row in [list(frame.columns), *_frame_rows(frame, limit=1000)]:
            worksheet.append(row)
        for cell in worksheet[1]:
            cell.font = Font(bold=True)
        worksheet.freeze_panes = "A2"
        for column in worksheet.columns:
            width = min(max(len(str(cell.value or "")) for cell in column) + 2, 42)
            worksheet.column_dimensions[
                get_column_letter(column[0].column)
            ].width = width
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
