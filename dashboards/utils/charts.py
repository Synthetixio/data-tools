import plotly.express as px
from typing import List, Optional, Union

# Constants
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


def update_layout(fig, orientation: str = "v", help_text: Optional[str] = None):
    """Apply common layout updates to the figure."""
    fig.update_xaxes(title_text="", automargin=True)
    fig.update_yaxes(title_text="")
    fig.update_traces(hovertemplate=None)

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
    if help_text:
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
                        bgcolor="#333333",
                        font_size=14,
                        font_color="white",
                    ),
                )
            ]
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
    help_text: Optional[str] = None,
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
    return update_layout(fig, help_text=help_text)


def chart_many_lines(
    df,
    x_col: str,
    y_cols: List[str],
    title: str,
    color: Optional[str] = None,
    x_format: str = "#",
    y_format: str = "$",
    help_text: Optional[str] = None,
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
    return update_layout(fig, help_text=help_text)


def chart_bars(
    df,
    x_col: str,
    y_cols: Union[str, List[str]],
    title: str,
    color: Optional[str] = None,
    x_format: str = "#",
    y_format: str = "$",
    column: bool = False,
    barmode: str = "relative",
    help_text: Optional[str] = None,
):
    """Create a bar chart."""
    fig = px.bar(
        df,
        x=x_col,
        y=y_cols,
        title=title,
        color=color,
        color_discrete_sequence=CATEGORICAL_COLORS,
        template=PLOTLY_TEMPLATE,
        orientation="h" if column else "v",
        barmode=barmode,
    )
    fig = set_axes(fig, x_format, y_format)
    return update_layout(fig, orientation="h" if column else "v", help_text=help_text)


def chart_area(
    df,
    x_col: str,
    y_cols: Union[str, List[str]],
    title: str,
    color: Optional[str] = None,
    x_format: str = "#",
    y_format: str = "$",
    column: bool = False,
    help_text: Optional[str] = None,
):
    """Create an area chart."""
    fig = px.area(
        df,
        x=x_col,
        y=y_cols,
        title=title,
        color=color,
        color_discrete_sequence=CATEGORICAL_COLORS,
        template=PLOTLY_TEMPLATE,
    )
    fig = set_axes(fig, x_format, y_format)
    return update_layout(fig, orientation="h" if column else "v", help_text=help_text)


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
    return update_layout(fig, help_text=help_text)


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
