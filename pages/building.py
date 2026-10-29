"""Building detail page: profile of one building (SRI domains, impacts, key functionalities, SbP topics)."""
import dash
import pandas as pd
from dash import Input, Output, callback, dcc, html

from components.data import building_options, fmt, get_building, get_data, label, sbp_level_name, tooltip, unit
from components.figures import (DOMAIN_COLS, IMPACT_COLS, KF_COLS, SBP_TOPIC_COLS, bar_scores,
                                heatmap_detailed, location_map)
from components.ui import GRAPH_CONFIG, GRAPH_CONFIG_RESPONSIVE, card, control, kpi_static

dash.register_page(__name__, path="/building", name="Building detail", order=1,
                   title="Building detail · NSBI Smart Buildings")

# Data-dictionary groups shown in the "Characteristics" and "Building performance" cards. All columns of these
# groups are used automatically, so parameters added to the Excel file appear without code changes.
CHARACTERISTIC_GROUPS = ["Identity", "Location", "Building", "Metadata"]
PERFORMANCE_GROUP = "Building performance"
NOT_IN_TABLE = {"building_name", "short_name"}  # already shown as the page title / chart labels
REFERENCE_FIELDS = [("main_reference", "main_reference_url"),
                    ("building_info_reference", "building_info_reference_url"),
                    ("performance_info_reference", "performance_info_reference_url")]


def layout(building_id=None, **_):
    opts = building_options()
    if building_id is None and opts:
        building_id = opts[0]["value"]
    return html.Div([
        html.Div(className="page-head", children=[
            html.H1("Building detail"),
            html.P("Smartness profile of a single building."),
        ]),
        card(control("Building", dcc.Dropdown(id="bd-select", options=opts, value=building_id, clearable=False))),
        html.Div(id="bd-content"),
    ])


def _group_columns(groups: list[str]) -> list[str]:
    d = get_data().dictionary
    ref_cols = {c for pair in REFERENCE_FIELDS for c in pair}
    return [c for c, g in zip(d["column"], d["group"]) if g in groups and c not in NOT_IN_TABLE and c not in ref_cols]


def _value_text(c: str, v) -> str:
    """Formatted value; the unit is appended when fmt() does not already include it."""
    text = fmt(c, v)
    u = unit(c)
    if u and not u.startswith("level") and u not in text:
        text = f"{text} {u}"
    return text


def _empty(v) -> bool:
    return v is None or (isinstance(v, float) and pd.isna(v)) or (isinstance(v, str) and not v.strip())


def _info_table(r: pd.Series) -> html.Table:
    """All non-empty characteristics of the building (identity, location, building, metadata) + references."""
    rows = []
    for c in _group_columns(CHARACTERISTIC_GROUPS):
        if c in r.index and not _empty(r[c]):
            rows.append(html.Tr([html.Th(label(c, with_unit=False), title=tooltip(c)), html.Td(_value_text(c, r[c]))]))
    for ref_col, url_col in REFERENCE_FIELDS:
        ref, url = r.get(ref_col), r.get(url_col)
        if isinstance(ref, str) and ref:
            cell = html.A(ref, href=url, target="_blank") if isinstance(url, str) and url else ref
            rows.append(html.Tr([html.Th(label(ref_col, with_unit=False), title=tooltip(ref_col)), html.Td(cell)]))
    return html.Table(rows, className="info-table")


def _performance_table(r: pd.Series) -> list:
    """All building performance indicators of the dataset, with the value or '–' when not available."""
    cols = [c for c in _group_columns([PERFORMANCE_GROUP]) if c in r.index]
    if not cols:
        return [html.P("No building performance parameters are defined in the dataset.", className="muted")]
    n_avail = sum(not _empty(r[c]) for c in cols)
    rows = [html.Tr([html.Th(label(c, with_unit=False), title=tooltip(c)),
                     html.Td("–", className="muted") if _empty(r[c]) else html.Td(_value_text(c, r[c]))])
            for c in cols]
    return [html.P(f"{n_avail} of {len(cols)} indicators available for this building. Hover a name for its "
                   "definition; intensities are per m² of conditioned floor area.", className="muted"),
            html.Table(rows, className="info-table")]


@callback(Output("bd-content", "children"), Input("bd-select", "value"))
def _render(building_id):
    r = get_building(building_id) if building_id else None
    if r is None:
        return card(html.P("Building not found."))
    det = get_data().detailed
    det = det[det["building_id"] == building_id]
    sbp = r.get("sbp_level")
    kpis = html.Div(className="kpi-row", children=[
        kpi_static("SRI total score", fmt("sri_total_pct", r.get("sri_total_pct")), str(r.get("sri_class") or ""),
                   description=tooltip("sri_total_pct") + "\n\n" + tooltip("sri_class")),
        kpi_static("SbP level", fmt("sbp_level", sbp), sbp_level_name(sbp), description=tooltip("sbp_level")),
        kpi_static("Location", str(r.get("city", "")), str(r.get("county", "")),
                   description="City and county of the building.\n" + tooltip("location_precision")),
        kpi_static("Period", str(r.get("construction_period", "")), str(r.get("building_category", "")),
                   description=tooltip("construction_period") + "\n\n" + tooltip("building_category")),
    ])
    has_detail = det.shape[0] > 0 or any(pd.notna(r.get(c)) for c in IMPACT_COLS)
    graphs = [
        html.Div(className="grid-2", children=[
            card(dcc.Graph(figure=bar_scores(r, KF_COLS, "SRI key functionalities [%]", (0, 100), 260),
                           config=GRAPH_CONFIG)),
            card(dcc.Graph(figure=bar_scores(r, SBP_TOPIC_COLS, "Smart by Powerhouse level per topic (−2 … 4)",
                                             (-2, 4), 260), config=GRAPH_CONFIG)),
        ]),
    ]
    if has_detail:
        graphs.append(html.Div(className="grid-2", children=[
            card(dcc.Graph(figure=bar_scores(r, IMPACT_COLS, "SRI impact criteria [%]", (0, 100), 360),
                           config=GRAPH_CONFIG)),
            card(dcc.Graph(figure=bar_scores(r, DOMAIN_COLS, "SRI technical domains [%]", (-50, 100), 360),
                           config=GRAPH_CONFIG)),
        ]))
        graphs.append(card(dcc.Graph(figure=heatmap_detailed(det), config=GRAPH_CONFIG)))
    else:
        graphs.append(card(html.P("Only total scores and key functionalities are published for this building; "
                                  "no impact, domain or detailed results are available.", className="muted")))
    return html.Div([
        html.H2(r["building_name"], className="building-title"),
        kpis,
        html.Div(className="grid-2 bd-top", children=[
            html.Div(className="bd-col", children=[
                card(_info_table(r), title="Characteristics"),
                card(_performance_table(r), title="Building performance"),
            ]),
            card(html.Div(dcc.Graph(figure=location_map(r), config=GRAPH_CONFIG_RESPONSIVE,
                                    style={"height": "100%", "width": "100%"}), className="map-fill"),
                 title="Location", className="map-card"),
        ]),
        *graphs,
    ])
