"""Small reusable layout blocks."""
from typing import Any

from dash import dcc, html

# Plotly options shared by all graphs (hide the Plotly logo in the mode bar). Typed as Any because dcc.Graph's
# `config` prop is a TypedDict in Dash 3+, which makes IDEs flag a plain dict literal.
# noinspection SpellCheckingInspection
GRAPH_CONFIG: Any = {"displaylogo": False}  # 'displaylogo' is Plotly's option name
GRAPH_CONFIG_RESPONSIVE: Any = {**GRAPH_CONFIG, "responsive": True}  # graph resizes with its container


def card(children, title: str | None = None, subtitle: str | None = None, className: str = "") -> html.Div:
    head = []
    if title:
        head.append(html.H3(title, className="card-title"))
    if subtitle:
        head.append(html.P(subtitle, className="card-subtitle"))
    return html.Div(head + (children if isinstance(children, list) else [children]), className=f"card {className}")


def control(label: str, component) -> html.Div:
    return html.Div([html.Label(label, className="control-label"), component], className="control")


def kpi(label: str, value_id: str, sub_id: str | None = None, description: str = "") -> html.Div:
    """KPI card whose value is filled by a callback; `description` is shown on hover."""
    children = [html.Div(label, className="kpi-label"), html.Div("–", id=value_id, className="kpi-value")]
    if sub_id:
        children.append(html.Div("", id=sub_id, className="kpi-sub"))
    return html.Div(children, className="kpi", title=description or None)


def kpi_static(label: str, value: str, sub: str = "", description: str = "") -> html.Div:
    """KPI card with a fixed value; `description` is shown on hover."""
    return html.Div([html.Div(label, className="kpi-label"), html.Div(value, className="kpi-value"),
                     html.Div(sub, className="kpi-sub")], className="kpi", title=description or None)


def graph(gid: str, height: int | None = None, **kwargs) -> dcc.Loading:
    style = {"height": f"{height}px"} if height else {}
    return dcc.Loading(dcc.Graph(id=gid, config=GRAPH_CONFIG, style=style, **kwargs), type="default")
