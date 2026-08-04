"""Reusable Plotly figures for the Academic Audit Analytics Tool.

The functions in this module are presentation-framework independent: callers
provide tabular data and receive a configured :class:`plotly.graph_objects.Figure`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.constants import CHART_COLORS

BACKGROUND_COLOR = "#0B1120"
PAPER_COLOR = "#111827"
CARD_COLOR = "#172033"
GRID_COLOR = "#263247"
TEXT_COLOR = "#E5E7EB"
MUTED_TEXT_COLOR = "#94A3B8"
FONT_FAMILY = "Inter, Segoe UI, sans-serif"
COLOR_SEQUENCE = tuple(CHART_COLORS.values())
DISPLAY_LABEL_COLUMN = "_display_category"
FULL_LABEL_COLUMN = "_full_category"


def _to_dataframe(data: pd.DataFrame | Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    """Return a copy of supported tabular input as a DataFrame."""
    if isinstance(data, pd.DataFrame):
        return data.copy()
    return pd.DataFrame.from_records(data)


def _require_columns(data: pd.DataFrame, *columns: str) -> None:
    """Raise a helpful error when a requested chart column is absent."""
    missing_columns = [column for column in columns if column not in data.columns]
    if missing_columns:
        raise ValueError(
            f"Chart data is missing required column(s): {', '.join(missing_columns)}"
        )


def _wrap_label(value: object, width: int = 18) -> str:
    """Wrap a category label at word boundaries for compact chart axes."""
    words = str(value).split()
    if not words:
        return "—"

    lines: list[str] = []
    current_line = ""
    for word in words:
        candidate = f"{current_line} {word}".strip()
        if current_line and len(candidate) > width:
            lines.append(current_line)
            current_line = word
        else:
            current_line = candidate
    lines.append(current_line)
    return "<br>".join(lines)


def _abbreviate_department_name(label: str) -> str:
    """Shorten common department wording for axes while retaining full hovers."""
    return (
        label.replace(" and ", " & ")
        .replace("Engineering", "Eng.")
        .replace("Technology", "Tech.")
        .replace("Management", "Mgmt.")
    )


def _prepare_category_labels(data: pd.DataFrame, column: str) -> pd.DataFrame:
    """Add display and full-label columns without altering analytical values."""
    frame = data.copy()
    full_labels = frame[column].fillna("—").astype(str)
    display_labels = full_labels
    if column == "department_name":
        display_labels = display_labels.map(_abbreviate_department_name)
    frame[FULL_LABEL_COLUMN] = full_labels
    frame[DISPLAY_LABEL_COLUMN] = display_labels.map(_wrap_label)
    return frame


def _empty_figure(title: str) -> go.Figure:
    """Return a stable, friendly empty state for charts with no result rows."""
    figure = go.Figure()
    apply_standard_layout(figure, title, show_legend=False)
    figure.add_annotation(
        text="No records found for the selected filters.",
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 15, "color": MUTED_TEXT_COLOR},
    )
    figure.update_xaxes(visible=False)
    figure.update_yaxes(visible=False)
    return figure


def get_theme() -> dict[str, Any]:
    """Return the shared dark Plotly theme configuration."""
    return {
        "template": "plotly_dark",
        "paper_bgcolor": PAPER_COLOR,
        "plot_bgcolor": BACKGROUND_COLOR,
        "font": {"family": FONT_FAMILY, "color": TEXT_COLOR},
        "colorway": COLOR_SEQUENCE,
    }


def get_color_palette() -> dict[str, str]:
    """Return a mutable copy of the shared semantic chart palette."""
    return dict(CHART_COLORS)


def get_export_config(filename: str = "academic-audit-chart") -> dict[str, Any]:
    """Return a Plotly export configuration suitable for any host application."""
    return {
        "displaylogo": False,
        "responsive": True,
        "toImageButtonOptions": {"format": "png", "filename": filename, "scale": 2},
    }


def apply_standard_layout(
    figure: go.Figure,
    title: str | None = None,
    height: int = 405,
    show_legend: bool = True,
) -> go.Figure:
    """Apply the common premium dark layout and responsive hover behavior."""
    figure.update_layout(
        **get_theme(),
        title={"text": title, "x": 0.02, "xanchor": "left", "font": {"size": 19}},
        height=height,
        margin={"l": 54, "r": 34, "t": 68, "b": 76},
        hovermode="closest",
        hoverlabel={
            "bgcolor": CARD_COLOR,
            "font": {"family": FONT_FAMILY, "color": TEXT_COLOR},
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
        showlegend=show_legend,
    )
    figure.update_xaxes(
        showgrid=False,
        linecolor=GRID_COLOR,
        tickfont={"color": MUTED_TEXT_COLOR, "size": 12},
        automargin=True,
    )
    figure.update_yaxes(
        gridcolor=GRID_COLOR,
        zerolinecolor=GRID_COLOR,
        tickfont={"color": MUTED_TEXT_COLOR, "size": 12},
        automargin=True,
    )
    return figure


def create_kpi_card(
    label: str,
    value: float,
    delta: float | None = None,
    suffix: str = "",
    prefix: str = "",
    subtitle: str = "Updated for selected filters",
) -> go.Figure:
    """Create a compact, reusable KPI indicator card."""
    indicator: dict[str, Any] = {
        "mode": "number" if delta is None else "number+delta",
        "value": value,
        "number": {
            "prefix": prefix,
            "suffix": suffix,
            "font": {"size": 38, "color": TEXT_COLOR},
        },
        "title": {
            "text": f"{label}<br><span style='font-size:11px'>{subtitle}</span>",
            "font": {"size": 15, "color": MUTED_TEXT_COLOR},
        },
    }
    if delta is not None:
        indicator["delta"] = {
            "reference": value - delta,
            "relative": False,
            "valueformat": ".2f",
        }
    figure = go.Figure(go.Indicator(**indicator))
    figure.update_layout(
        **get_theme(),
        height=168,
        margin={"l": 24, "r": 24, "t": 32, "b": 24},
    )
    return figure


def create_bar_chart(
    data: pd.DataFrame | Sequence[Mapping[str, Any]],
    x: str,
    y: str,
    title: str,
    color: str | None = None,
) -> go.Figure:
    """Create a vertical bar chart from tabular data."""
    frame = _to_dataframe(data)
    if frame.empty:
        return _empty_figure(title)
    _require_columns(frame, x, y)
    frame = _prepare_category_labels(frame, x)
    figure = px.bar(
        frame,
        x=DISPLAY_LABEL_COLUMN,
        y=y,
        color=color,
        custom_data=[FULL_LABEL_COLUMN],
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    figure.update_traces(
        hovertemplate=f"%{{customdata[0]}}<br>{y.replace('_', ' ').title()}: %{{y}}<extra></extra>"
    )
    return apply_standard_layout(figure, title, show_legend=color is not None)


def create_horizontal_bar_chart(
    data: pd.DataFrame | Sequence[Mapping[str, Any]],
    category: str,
    value: str,
    title: str,
    color: str | None = None,
) -> go.Figure:
    """Create a horizontal bar chart suited to ranking comparisons."""
    frame = _to_dataframe(data)
    if frame.empty:
        return _empty_figure(title)
    _require_columns(frame, category, value)
    frame = _prepare_category_labels(frame, category)
    figure = px.bar(
        frame,
        x=value,
        y=DISPLAY_LABEL_COLUMN,
        color=color,
        orientation="h",
        custom_data=[FULL_LABEL_COLUMN],
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    figure.update_traces(
        hovertemplate=f"%{{customdata[0]}}<br>{value.replace('_', ' ').title()}: %{{x}}<extra></extra>"
    )
    return apply_standard_layout(figure, title, show_legend=color is not None)


def create_pie_chart(
    data: pd.DataFrame | Sequence[Mapping[str, Any]],
    names: str,
    values: str,
    title: str,
) -> go.Figure:
    """Create a pie chart with the shared categorical palette."""
    frame = _to_dataframe(data)
    if frame.empty:
        return _empty_figure(title)
    _require_columns(frame, names, values)
    figure = px.pie(
        frame,
        names=names,
        values=values,
        color=names,
        color_discrete_sequence=COLOR_SEQUENCE,
        hole=0,
    )
    figure.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="%{label}: %{value}<br>%{percent}<extra></extra>",
    )
    return apply_standard_layout(figure, title)


def create_donut_chart(
    data: pd.DataFrame | Sequence[Mapping[str, Any]],
    names: str,
    values: str,
    title: str,
) -> go.Figure:
    """Create a donut chart for compact composition analysis."""
    figure = create_pie_chart(data, names, values, title)
    figure.update_traces(hole=0.58)
    return figure


def create_line_chart(
    data: pd.DataFrame | Sequence[Mapping[str, Any]],
    x: str,
    y: str,
    title: str,
    color: str | None = None,
) -> go.Figure:
    """Create a line chart, optionally split into series by ``color``."""
    frame = _to_dataframe(data)
    if frame.empty:
        return _empty_figure(title)
    _require_columns(frame, x, y)
    frame = _prepare_category_labels(frame, x)
    figure = px.line(
        frame,
        x=DISPLAY_LABEL_COLUMN,
        y=y,
        color=color,
        markers=True,
        custom_data=[FULL_LABEL_COLUMN],
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    figure.update_traces(
        hovertemplate=f"%{{customdata[0]}}<br>{y.replace('_', ' ').title()}: %{{y}}<extra></extra>"
    )
    return apply_standard_layout(figure, title, show_legend=color is not None)


def create_area_chart(
    data: pd.DataFrame | Sequence[Mapping[str, Any]],
    x: str,
    y: str,
    title: str,
    color: str | None = None,
) -> go.Figure:
    """Create an area chart for cumulative or changing values."""
    frame = _to_dataframe(data)
    _require_columns(frame, x, y)
    figure = px.area(
        frame, x=x, y=y, color=color, color_discrete_sequence=COLOR_SEQUENCE
    )
    return apply_standard_layout(figure, title, show_legend=color is not None)


def create_scatter_chart(
    data: pd.DataFrame | Sequence[Mapping[str, Any]],
    x: str,
    y: str,
    title: str,
    color: str | None = None,
    size: str | None = None,
) -> go.Figure:
    """Create a scatter chart for relationship analysis."""
    frame = _to_dataframe(data)
    _require_columns(frame, x, y)
    figure = px.scatter(
        frame, x=x, y=y, color=color, size=size, color_discrete_sequence=COLOR_SEQUENCE
    )
    return apply_standard_layout(figure, title, show_legend=color is not None)


def create_histogram(
    data: pd.DataFrame | Sequence[Mapping[str, Any]],
    value: str,
    title: str,
    color: str | None = None,
) -> go.Figure:
    """Create a distribution histogram."""
    frame = _to_dataframe(data)
    _require_columns(frame, value)
    figure = px.histogram(
        frame, x=value, color=color, color_discrete_sequence=COLOR_SEQUENCE
    )
    return apply_standard_layout(figure, title, show_legend=color is not None)


def create_box_plot(
    data: pd.DataFrame | Sequence[Mapping[str, Any]],
    category: str,
    value: str,
    title: str,
    color: str | None = None,
) -> go.Figure:
    """Create a box plot for score spread and outlier analysis."""
    frame = _to_dataframe(data)
    _require_columns(frame, category, value)
    figure = px.box(
        frame, x=category, y=value, color=color, color_discrete_sequence=COLOR_SEQUENCE
    )
    return apply_standard_layout(figure, title, show_legend=color is not None)


def create_heatmap(
    data: pd.DataFrame | Sequence[Mapping[str, Any]],
    x: str,
    y: str,
    value: str,
    title: str,
) -> go.Figure:
    """Create a heatmap from long-form tabular data."""
    frame = _to_dataframe(data)
    _require_columns(frame, x, y, value)
    matrix = frame.pivot_table(index=y, columns=x, values=value, aggfunc="mean")
    figure = px.imshow(matrix, color_continuous_scale="Viridis", aspect="auto")
    return apply_standard_layout(figure, title, show_legend=False)


def create_treemap(
    data: pd.DataFrame | Sequence[Mapping[str, Any]],
    path: Sequence[str],
    values: str,
    title: str,
    color: str | None = None,
) -> go.Figure:
    """Create a hierarchical treemap from category path columns."""
    frame = _to_dataframe(data)
    _require_columns(frame, *path, values)
    figure = px.treemap(
        frame,
        path=list(path),
        values=values,
        color=color,
        color_continuous_scale="Teal",
    )
    return apply_standard_layout(figure, title)


def create_grouped_bar_chart(
    data: pd.DataFrame | Sequence[Mapping[str, Any]],
    x: str,
    y: str,
    group: str,
    title: str,
) -> go.Figure:
    """Create grouped bars for category-to-category comparison."""
    frame = _to_dataframe(data)
    _require_columns(frame, x, y, group)
    figure = px.bar(
        frame,
        x=x,
        y=y,
        color=group,
        barmode="group",
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    return apply_standard_layout(figure, title)


def create_comparison_chart(
    data: pd.DataFrame | Sequence[Mapping[str, Any]],
    category: str,
    metrics: Sequence[str],
    title: str,
) -> go.Figure:
    """Create a multi-metric grouped comparison chart from wide data."""
    frame = _to_dataframe(data)
    if frame.empty:
        return _empty_figure(title)
    _require_columns(frame, category, *metrics)
    frame = _prepare_category_labels(frame, category)
    figure = go.Figure()
    for index, metric in enumerate(metrics):
        figure.add_bar(
            name=metric.replace("_", " ").title(),
            x=frame[DISPLAY_LABEL_COLUMN],
            y=frame[metric],
            customdata=frame[[FULL_LABEL_COLUMN]],
            hovertemplate=(
                f"%{{customdata[0]}}<br>{metric.replace('_', ' ').title()}: "
                "%{y}<extra></extra>"
            ),
            marker_color=COLOR_SEQUENCE[index % len(COLOR_SEQUENCE)],
        )
    figure.update_layout(barmode="group")
    return apply_standard_layout(figure, title)


def create_trend_chart(
    data: pd.DataFrame | Sequence[Mapping[str, Any]],
    period: str,
    value: str,
    title: str,
    series: str | None = None,
) -> go.Figure:
    """Create a semantic alias for a time or semester trend line chart."""
    return create_line_chart(data, period, value, title, series)
