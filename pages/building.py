"""Building detail page: profile of one building (SRI domains, impacts, key functionalities, SbP topics)."""
import dash
import pandas as pd
from dash import Input, Output, callback, dcc, html

from components.data import building_options, fmt, get_building, get_data, label, sbp_level_name
from components.figures import (DOMAIN_COLS, IMPACT_COLS, KF_COLS, SBP_TOPIC_COLS, bar_scores,
                                heatmap_detailed, location_map)
from components.ui import card, control, kpi_static

dash.register_page(__name__, path="/building", name="Building detail", order=1,
                   title="Building detail · NSBI Smart Buildings")

INFO_FIELDS = ["building_id", "owner_partner", "address", "city", "municipality", "county", "building_type",
               "floor_area_category", "floor_area_m2", "construction_period", "construction_year",
               "latest_renovation_year", "assessed_state", "n_sri_domains_assessed", "sri_domains_not_assessed",
               "location_precision", "assessment_year", "sri_method", "sbp_tool", "notes"]
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


def _info_table(r: pd.Series) -> html.Table:
    rows = []
    for c in INFO_FIELDS:
        if c in r.index and not (pd.isna(r[c]) or r[c] == ""):
            rows.append(html.Tr([html.Th(label(c, with_unit=False)), html.Td(fmt(c, r[c]))]))
    for ref_col, url_col in REFERENCE_FIELDS:
        ref, url = r.get(ref_col), r.get(url_col)
        if isinstance(ref, str) and ref:
            cell = html.A(ref, href=url, target="_blank") if isinstance(url, str) and url else ref
            rows.append(html.Tr([html.Th(label(ref_col, with_unit=False)), html.Td(cell)]))
    return html.Table(rows, className="info-table")


@callback(Output("bd-content", "children"), Input("bd-select", "value"))
def _render(building_id):
    r = get_building(building_id) if building_id else None
    if r is None:
        return card(html.P("Building not found."))
    det = get_data().detailed
    det = det[det["building_id"] == building_id]
    sbp = r.get("sbp_level")
    kpis = html.Div(className="kpi-row", children=[
        kpi_static("SRI total score", fmt("sri_total_pct", r.get("sri_total_pct")), str(r.get("sri_class") or "")),
        kpi_static("SbP level", fmt("sbp_level", sbp), sbp_level_name(sbp)),
        kpi_static("Location", str(r.get("city", "")), str(r.get("county", ""))),
        kpi_static("Period", str(r.get("construction_period", "")), str(r.get("building_category", ""))),
    ])
    has_detail = det.shape[0] > 0 or any(pd.notna(r.get(c)) for c in IMPACT_COLS)
    graphs = [
        html.Div(className="grid-2", children=[
            card(dcc.Graph(figure=bar_scores(r, KF_COLS, "SRI key functionalities [%]", (0, 100), 260),
                           config={"displaylogo": False})),
            card(dcc.Graph(figure=bar_scores(r, SBP_TOPIC_COLS, "Smart by Powerhouse level per topic (−2 … 4)",
                                             (-2, 4), 260), config={"displaylogo": False})),
        ]),
    ]
    if has_detail:
        graphs.append(html.Div(className="grid-2", children=[
            card(dcc.Graph(figure=bar_scores(r, IMPACT_COLS, "SRI impact criteria [%]", (0, 100), 360),
                           config={"displaylogo": False})),
            card(dcc.Graph(figure=bar_scores(r, DOMAIN_COLS, "SRI technical domains [%]", (-50, 100), 360),
                           config={"displaylogo": False})),
        ]))
        graphs.append(card(dcc.Graph(figure=heatmap_detailed(det), config={"displaylogo": False})))
    else:
        graphs.append(card(html.P("Only total scores and key functionalities are published for this building; "
                                  "no impact, domain or detailed results are available.", className="muted")))
    return html.Div([
        html.H2(r["building_name"], className="building-title"),
        kpis,
        html.Div(className="grid-2", children=[
            card(_info_table(r), title="Characteristics"),
            card(dcc.Graph(figure=location_map(r), config={"displaylogo": False}), title="Location"),
        ]),
        *graphs,
    ])
