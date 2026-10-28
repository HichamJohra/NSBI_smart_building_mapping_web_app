"""Small reusable layout blocks."""
from dash import dcc, html


def card(children, title: str | None = None, subtitle: str | None = None, className: str = "") -> html.Div:
    head = []
    if title:
        head.append(html.H3(title, className="card-title"))
    if subtitle:
        head.append(html.P(subtitle, className="card-subtitle"))
    return html.Div(head + (children if isinstance(children, list) else [children]), className=f"card {className}")


def control(label: str, component) -> html.Div:
    return html.Div([html.Label(label, className="control-label"), component], className="control")


def kpi(label: str, value_id: str, sub_id: str | None = None) -> html.Div:
    children = [html.Div(label, className="kpi-label"), html.Div("–", id=value_id, className="kpi-value")]
    if sub_id:
        children.append(html.Div("", id=sub_id, className="kpi-sub"))
    return html.Div(children, className="kpi")


def kpi_static(label: str, value: str, sub: str = "") -> html.Div:
    return html.Div([html.Div(label, className="kpi-label"), html.Div(value, className="kpi-value"),
                     html.Div(sub, className="kpi-sub")], className="kpi")


def graph(gid: str, height: int | None = None, **kwargs) -> dcc.Loading:
    style = {"height": f"{height}px"} if height else {}
    return dcc.Loading(dcc.Graph(id=gid, config={"displaylogo": False}, style=style, **kwargs), type="default")
