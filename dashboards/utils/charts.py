import plotly.express as px
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import List, Optional, Union, Any, Dict
from dashboards.utils.formatting import human_format as format_func

# Constants
AGGS = {
    "sum": np.sum,
}
HOVER_PREFIX_MAP = {"$": "$", "#": "", "%": "%"}
SEQUENTIAL_COLORS = [
    "#E5FAFF",
    "#B7F2FF",
    "#8AEAFF",
    "#5CE1FF",
    "#2FD9FF",
    "#00D1FF",
    "#00B0D6",
    "#006D85",
    "#004B5C",
]
CATEGORICAL_COLORS = ["#00D1FF", "#EB46FF", "#6B59FF", "#4FD1C5", "#1F68AC", "#FDE8FF"]
FONT_FAMILY = "sans-serif"
PLOTLY_TEMPLATE = "plotly_dark"
DEFAULT_LINE_COLOR = "white"
DEFAULT_LINE_WIDTH = 0
HELP_TEXT_BGCOLOR = "#333333"
HELP_TEXT_FONT_SIZE = 14
HELP_TEXT_FONT_COLOR = "white"


def set_axes(fig, x_format: str, y_format: str):
    """Format axes based on specified formats."""
    format_map = {"%": ".2%", "$": "$", "#": None}

    fig.update_yaxes(
        tickformat=format_map[y_format] if y_format == "%" else None,
        tickprefix=format_map[y_format] if y_format != "%" else None,
    )
    fig.update_xaxes(
        tickformat=format_map[x_format] if x_format == "%" else None,
        tickprefix=format_map[x_format] if x_format != "%" else None,
    )

    return fig


def update_layout(
    fig,
    orientation: str = "v",
    help_text: Optional[str] = None,
):
    """Apply common layout updates to the figure.

    Args:
        fig: The plotly figure to update.
        orientation: The orientation of the chart ("v" for vertical, "h" for horizontal).
        help_text: Optional text to display in the top-right corner of the chart.
        custom_data: Optional data to add to the chart.
        hover_template: Optional template for the chart's hover tooltip.
    """
    fig.update_xaxes(title_text="", automargin=True)
    fig.update_yaxes(title_text="")
    if help_text is not None:
        fig.update_layout(
            annotations=[
                dict(
                    x=1,
                    y=1.25,
                    xref="paper",
                    yref="paper",
                    text="❔",
                    showarrow=False,
                    font=dict(size=20),
                    xanchor="right",
                    yanchor="top",
                    hovertext=help_text,
                    hoverlabel=dict(
                        bgcolor=HELP_TEXT_BGCOLOR,
                        font_size=HELP_TEXT_FONT_SIZE,
                        font_color=HELP_TEXT_FONT_COLOR,
                    ),
                )
            ]
        )
    fig.update_layout(
        hovermode=f"{'y' if orientation == 'h' else 'x'} unified",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.2,
            xanchor="center",
            x=0.5,
            title=None,
        ),
        font=dict(family=FONT_FAMILY),
    )
    return fig


def chart_many_bars(
    df,
    x_col: str,
    y_cols: List[str],
    title: str,
    color: Optional[str] = None,
    x_format: str = "#",
    y_format: str = "$",
):
    """Create a bar chart with multiple series."""
    fig = px.bar(
        df,
        x=x_col,
        y=y_cols,
        title=title,
        color=color,
        color_discrete_sequence=CATEGORICAL_COLORS,
        template=PLOTLY_TEMPLATE,
    )
    fig = set_axes(fig, x_format, y_format)
    fig.update_xaxes(title_text="", automargin=True)
    fig.update_yaxes(title_text="")
    fig.update_layout(
        font=dict(family=FONT_FAMILY),
    )
    return fig


def chart_many_lines(
    df,
    x_col: str,
    y_cols: List[str],
    title: str,
    color: Optional[str] = None,
    x_format: str = "#",
    y_format: str = "$",
):
    """Create a line chart with multiple series."""
    fig = px.line(
        df,
        x=x_col,
        y=y_cols,
        title=title,
        color=color,
        color_discrete_sequence=CATEGORICAL_COLORS,
        template=PLOTLY_TEMPLATE,
    )
    fig = set_axes(fig, x_format, y_format)
    return fig


def chart_bars(
    df,
    x_col: str,
    y_cols: Union[str, List[str]],
    title: str,
    color_by: Optional[str] = None,
    x_format: str = "#",
    y_format: str = "$",
    column: bool = False,
    barmode: str = "relative",
    help_text: Optional[str] = None,
    human_format: bool = False,
    custom_agg: Optional[Dict[str, str]] = None,
    sort_by_last_value: bool = False,
    sort_ascending: bool = False,
):
    """Create a bar chart."""
    traces = _create_traces(
        df,
        x_col,
        y_cols,
        color_by,
        custom_agg,
        human_format,
        sort_by_last_value,
        sort_ascending,
        y_format,
    )
    fig = go.Figure(traces)
    fig.update_layout(
        title=title,
        template=PLOTLY_TEMPLATE,
        font=dict(family=FONT_FAMILY),
        barmode=barmode,
    )
    fig = set_axes(fig, x_format, y_format)
    return update_layout(
        fig,
        orientation="h" if column else "v",
        help_text=help_text,
    )


def chart_area(
    df,
    x_col: str,
    y_cols: List[str],
    title: str,
    color_by: Optional[str] = None,
    x_format: str = "#",
    y_format: str = "$",
    column: bool = False,
    sort_by_last_value: bool = False,
    sort_ascending: bool = False,
    help_text: Optional[str] = None,
    human_format: bool = False,
    custom_agg: Optional[Dict[str, str]] = None,
):
    """Create an area chart."""
    traces = _create_traces(
        df,
        x_col,
        y_cols,
        color_by,
        custom_agg,
        human_format,
        sort_by_last_value,
        sort_ascending,
        y_format,
    )
    fig = go.Figure(traces)
    fig.update_layout(
        title=title,
        template=PLOTLY_TEMPLATE,
        font=dict(family=FONT_FAMILY),
    )
    fig = set_axes(fig, x_format, y_format)
    return update_layout(
        fig,
        orientation="h" if column else "v",
        help_text=help_text,
    )


def chart_lines(
    df,
    x_col: str,
    y_cols: Union[str, List[str]],
    title: str,
    color: Optional[str] = None,
    smooth: bool = False,
    x_format: str = "#",
    y_format: str = "$",
    help_text: Optional[str] = None,
):
    """Create a line chart."""
    fig = px.line(
        df,
        x=x_col,
        y=y_cols,
        title=title,
        color=color,
        color_discrete_sequence=CATEGORICAL_COLORS,
        template=PLOTLY_TEMPLATE,
    )
    fig.update_traces(line_shape=None if smooth else "hv")
    fig = set_axes(fig, x_format, y_format)
    return update_layout(
        fig,
        help_text=help_text,
    )


def chart_oi(df, x_col: str, title: str, help_text: Optional[str] = None):
    """Create an Open Interest chart."""
    fig = px.area(
        df,
        x=x_col,
        y=["short_oi_pct", "long_oi_pct"],
        line_shape="hv",
        color_discrete_sequence=["red", "green"],
        title=title,
    )
    fig.update_yaxes(tickformat=".0%")
    return update_layout(fig, help_text=help_text)


def _create_traces(
    df,
    x_col: str,
    y_cols: List[str],
    color_by: Optional[str] = None,
    custom_agg: Optional[Dict[str, str]] = None,
    human_format: bool = False,
    sort_by_last_value: bool = False,
    sort_ascending: bool = False,
    y_format: str = "$",
):
    traces = []
    if color_by is not None:
        for i, (label, group) in enumerate(df.groupby(color_by)):
            _color = CATEGORICAL_COLORS[i % len(CATEGORICAL_COLORS)]
            traces.append(
                go.Scatter(
                    x=group[x_col],
                    y=group[y_cols],
                    name=label,
                    legendrank=0,
                    line=dict(width=2, color=_color),
                    mode="lines",
                    stackgroup="one",
                    customdata=(
                        group[y_cols].apply(format_func)
                        if human_format
                        else group[y_cols]
                    ),
                    hovertemplate=f"<extra></extra>%{{fullData.name}}: {HOVER_PREFIX_MAP[y_format]}%{{customdata}}",
                )
            )
    else:
        for i, y_col in enumerate(y_cols):
            _color = CATEGORICAL_COLORS[i % len(CATEGORICAL_COLORS)]
            traces.append(
                go.Scatter(
                    x=df[x_col],
                    y=df[y_col],
                    name=y_col,
                    legendrank=0,
                    line=dict(width=2, color=_color),
                )
            )
    if sort_by_last_value:
        traces.sort(key=lambda trace: trace["y"][-1], reverse=not sort_ascending)
    for rank, trace in enumerate(traces):
        trace["legendrank"] = rank

    if custom_agg is not None:
        for custom_agg in custom_agg:
            field = custom_agg.get("field")
            name = custom_agg.get("name", "Custom Field")
            agg = custom_agg.get("agg", "sum")
            y = df.groupby(x_col)[field].agg(AGGS[agg]).reset_index()
            traces.append(
                go.Scatter(
                    x=y[x_col],
                    y=y[field],
                    name=name,
                    legendrank=1000,
                    line=dict(width=0),
                    customdata=(
                        y[field].apply(format_func) if human_format else y[field]
                    ),
                    showlegend=False,
                    hovertemplate=f"<extra></extra><b>%{{fullData.name}}: {HOVER_PREFIX_MAP[y_format]}%{{customdata}}</b>",
                )
            )

    return traces
