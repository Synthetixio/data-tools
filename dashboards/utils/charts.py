import numpy as np
from typing import List, Optional, Union, Dict

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dashboards.utils.formatting import human_format as format_func

# Constants
HOVER_PREFIX_MAP = {"$": "$", "#": "", "%": ""}
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
OI_COLORS = ["red", "green"]
FONT_FAMILY = "sans-serif"
PLOTLY_TEMPLATE = "plotly_dark"
DEFAULT_LINE_COLOR = "white"
DEFAULT_LINE_WIDTH = 0
HELP_TEXT_BGCOLOR = "#333333"
HELP_TEXT_FONT_SIZE = 14
HELP_TEXT_FONT_COLOR = "white"


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
    human_format: bool = True,
    custom_agg: Optional[Dict[str, str]] = None,
    sort_by_last_value: bool = True,
    sort_ascending: bool = False,
    unified_hover: bool = True,
    no_decimals: bool = False,
):
    """Create a bar chart."""
    if isinstance(y_cols, str):
        traces = _create_traces_from_string(
            df=df,
            x_col=x_col,
            y_cols=y_cols,
            trace_type="bar",
            color_by=color_by,
            human_format=human_format,
            y_format=y_format,
            no_decimals=no_decimals,
        )
    else:
        traces = _create_traces_from_list(
            df=df,
            x_col=x_col,
            y_cols=y_cols,
            trace_type="bar",
            human_format=human_format,
            y_format=y_format,
            no_decimals=no_decimals,
        )
    if sort_by_last_value:
        traces = sort_traces(traces, sort_ascending)
    if custom_agg is not None:
        traces = add_aggregation(traces, custom_agg, df, x_col, y_format, human_format)
    fig = go.Figure(
        traces,
        layout=dict(
            title=title,
            template=PLOTLY_TEMPLATE,
            font=dict(family=FONT_FAMILY),
            barmode=barmode,
            legend_traceorder="reversed",
        ),
    )
    fig = set_axes(fig, x_format, y_format)
    if help_text is not None:
        fig = add_help_text(fig, help_text)
    if unified_hover:
        fig = clear_axes(fig)
        fig = set_hovermode_unified(fig, orientation="h" if column else "v")
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


def chart_area(
    df,
    x_col: str,
    y_cols: List[str],
    title: str,
    color_by: Optional[str] = None,
    x_format: str = "#",
    y_format: str = "$",
    column: bool = False,
    sort_by_last_value: bool = True,
    sort_ascending: bool = False,
    help_text: Optional[str] = None,
    human_format: bool = True,
    custom_agg: Optional[Dict[str, str]] = None,
    unified_hover: bool = True,
    no_decimals: bool = False,
):
    """Create an area chart."""
    if isinstance(y_cols, str):
        traces = _create_traces_from_string(
            df=df,
            x_col=x_col,
            y_cols=y_cols,
            trace_type="area",
            color_by=color_by,
            human_format=human_format,
            y_format=y_format,
            stackgroup="one",
            no_decimals=no_decimals,
        )
    else:
        traces = _create_traces_from_list(
            df=df,
            x_col=x_col,
            y_cols=y_cols,
            trace_type="area",
            human_format=human_format,
            y_format=y_format,
            stackgroup="one",
            no_decimals=no_decimals,
        )
    if sort_by_last_value:
        traces = sort_traces(traces, sort_ascending)
    if custom_agg is not None:
        traces = add_aggregation(traces, custom_agg, df, x_col, y_format, human_format)
    fig = go.Figure(
        traces,
        layout=dict(
            title=title,
            template=PLOTLY_TEMPLATE,
            font=dict(family=FONT_FAMILY),
        ),
    )
    fig = set_axes(fig, x_format, y_format)
    if help_text is not None:
        fig = add_help_text(fig, help_text)
    if unified_hover:
        fig = clear_axes(fig)
        fig = set_hovermode_unified(fig, orientation="h" if column else "v")
    return fig


def chart_lines(
    df,
    x_col: str,
    y_cols: Union[str, List[str]],
    title: str,
    color_by: Optional[str] = None,
    smooth: bool = False,
    x_format: str = "#",
    y_format: str = "$",
    help_text: Optional[str] = None,
    sort_by_last_value: bool = True,
    sort_ascending: bool = False,
    human_format: bool = True,
    custom_agg: Optional[Dict[str, str]] = None,
    unified_hover: bool = True,
    no_decimals: bool = False,
):
    """Create a line chart."""
    if isinstance(y_cols, str):
        traces = _create_traces_from_string(
            df=df,
            x_col=x_col,
            y_cols=y_cols,
            trace_type="line",
            color_by=color_by,
            human_format=human_format,
            y_format=y_format,
            stackgroup="",
            no_decimals=no_decimals,
        )
    else:
        traces = _create_traces_from_list(
            df=df,
            x_col=x_col,
            y_cols=y_cols,
            trace_type="line",
            human_format=human_format,
            y_format=y_format,
            stackgroup="",
            no_decimals=no_decimals,
        )
    if sort_by_last_value:
        traces = sort_traces(traces, sort_ascending)
    if custom_agg is not None:
        traces = add_aggregation(traces, custom_agg, df, x_col, y_format, human_format)
    fig = go.Figure(traces)
    fig.update_layout(
        title=title,
        template=PLOTLY_TEMPLATE,
        font=dict(family=FONT_FAMILY),
    )
    if help_text is not None:
        fig = add_help_text(fig, help_text)
    fig.update_traces(line_shape=None if smooth else "hv")
    fig = set_axes(fig, x_format, y_format)
    if not sort_ascending:
        fig.update_layout(legend_traceorder="reversed")
    if unified_hover:
        fig = clear_axes(fig)
        fig = set_hovermode_unified(fig, orientation="v")
    return fig


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
    fig = clear_axes(fig)
    if help_text is not None:
        fig = add_help_text(fig, help_text)
    fig = set_hovermode_unified(fig)
    return fig


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


def clear_axes(fig):
    """Clear axes from the figure."""
    fig.update_xaxes(title_text="", automargin=True)
    fig.update_yaxes(title_text="")
    return fig


def set_hovermode_unified(fig, orientation: str = "v"):
    """Set the hover mode of the figure."""
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


def add_help_text(fig, help_text: str):
    """Add help text to the figure."""
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
    return fig


def sort_traces(traces, sort_ascending):
    traces.sort(
        key=lambda trace: trace["y"][-1] if len(trace["y"]) > 0 else 0,
        reverse=not sort_ascending,
    )
    for rank, trace in enumerate(traces):
        trace["legendrank"] = -rank
    return traces


def add_aggregation(traces, custom_agg, df, x_col, y_format, human_format):
    percentage = True if y_format == "%" else False
    no_decimals = False if y_format == "$" else True
    if custom_agg is not None:
        field = custom_agg.get("field")
        name = custom_agg.get("name", "Total")
        agg = custom_agg.get("agg", "sum")
        y = df.groupby(x_col)[field].agg(agg).reset_index()
        custom_data = (
            y[field].apply(
                format_func,
                args=(no_decimals, percentage),
            )
            if human_format
            else y[field]
        )
        hover_template = f"<extra></extra><b>%{{fullData.name}}: {HOVER_PREFIX_MAP[y_format]}%{{customdata}}</b>"
        trace = _create_trace(
            x=y[x_col],
            y=y[field],
            name=name,
            trace_type="line",
            linewidth=0,
            custom_data=custom_data,
            hover_template=hover_template,
            show_legend=False,
            legendrank=-1000,
        )
        traces.append(trace)
    return traces


def _create_traces_from_list(
    df,
    x_col: str,
    y_cols: List[str],
    trace_type: str = "bar",
    human_format: bool = True,
    y_format: str = "$",
    stackgroup: Optional[str] = "one",
    color_map: Optional[Dict[str, str]] = CATEGORICAL_COLORS,
    no_decimals: bool = False,
):
    traces = []
    percentage = True if y_format == "%" else False
    for i, y_col in enumerate(y_cols):
        color = color_map[i % len(color_map)]
        hover_template = f"<extra></extra>%{{fullData.name}}: {HOVER_PREFIX_MAP[y_format]}%{{customdata}}"
        custom_data = df[y_col]
        if human_format:
            custom_data = custom_data.apply(format_func, args=(no_decimals, percentage))
        trace = _create_trace(
            x=df[x_col],
            y=df[y_col],
            name=y_col,
            color=color,
            trace_type=trace_type,
            legendrank=0,
            custom_data=custom_data,
            hover_template=hover_template,
            show_legend=True,
            stackgroup=stackgroup,
        )
        traces.append(trace)
    return traces


def _create_traces_from_string(
    df,
    x_col: str,
    y_cols: str,
    trace_type: str = "bar",
    color_by: Optional[str] = None,
    human_format: bool = True,
    y_format: str = "$",
    stackgroup: Optional[str] = "one",
    color_map: Optional[Dict[str, str]] = CATEGORICAL_COLORS,
    no_decimals: bool = False,
):
    traces = []
    percentage = True if y_format == "%" else False
    if color_by is not None:
        if trace_type == "area":
            # Get all unique indexes
            all_indexes = pd.Index([])
            for _, group in df.groupby(color_by):
                all_indexes = all_indexes.union(group[x_col])

        for i, (label, group) in enumerate(df.groupby(color_by)):
            if trace_type == "area":
                # Reindex the group to include all x values
                group = group.set_index(x_col).reindex(all_indexes, fill_value=0)
            color = color_map[i % len(color_map)]
            custom_data = group[y_cols]
            if human_format:
                custom_data = custom_data.apply(
                    format_func, args=(no_decimals, percentage)
                )
            hover_template = f"<extra></extra>%{{fullData.name}}: {HOVER_PREFIX_MAP[y_format]}%{{customdata}}"
            trace = _create_trace(
                x=group.index if trace_type == "area" else group[x_col],
                y=group[y_cols],
                name=label,
                trace_type=trace_type,
                color=color,
                legendrank=0,
                stackgroup=stackgroup,
                custom_data=custom_data,
                hover_template=hover_template,
                show_legend=True,
            )
            traces.append(trace)
    else:
        color = color_map[0]
        hover_template = f"<extra></extra>%{{fullData.name}}: {HOVER_PREFIX_MAP[y_format]}%{{customdata}}"
        trace = _create_trace(
            x=df[x_col],
            y=df[y_cols],
            name=y_cols,
            color=color,
            trace_type=trace_type,
            legendrank=0,
            custom_data=df[y_cols].apply(format_func, args=(no_decimals, percentage)),
            hover_template=hover_template,
            show_legend=True,
        )
        traces.append(trace)
    return traces


def _create_trace(
    x: pd.Series,
    y: pd.Series,
    name: str,
    trace_type: str = "bar",
    color: str = "white",
    legendrank: int = 0,
    stackgroup: Optional[str] = None,
    custom_data: Optional[pd.Series] = None,
    hover_template: Optional[str] = None,
    show_legend: bool = True,
    linewidth: int = 2,
):
    if trace_type == "bar":
        return go.Bar(
            x=x,
            y=y,
            name=name,
            legendrank=legendrank,
            marker=dict(color=color),
            customdata=custom_data,
            hovertemplate=hover_template,
            showlegend=show_legend,
        )
    elif trace_type in ["line", "area"]:
        return go.Scatter(
            x=x,
            y=y,
            name=name,
            stackgroup=stackgroup,
            legendrank=legendrank,
            line=dict(width=linewidth, color=color),
            mode="lines",
            customdata=custom_data,
            hovertemplate=hover_template,
            showlegend=show_legend,
        )
    else:
        raise ValueError(f"Invalid trace type: {trace_type}")
