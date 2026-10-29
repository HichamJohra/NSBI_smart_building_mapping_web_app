"""Compare buildings page: overlay several buildings on radar and bar charts."""
import dash
from dash import Input, Output, callback, dcc, html

from components.data import building_options, fmt, get_data, label
from components.figures import DOMAIN_COLS, IMPACT_COLS, KF_COLS, SBP_TOPIC_COLS, grouped_bars, radar
from components.ui import GRAPH_CONFIG, card, control

dash.register_page(__name__, path="/compare", name="Compare smartness", order=2, title="Compare · NSBI Smart Buildings")

MAX_BUILDINGS = 6
TABLE_FIELDS = ["city", "building_category", "construction_period", "sri_total_pct", "sri_class",
                "sri_kf1_building_pct", "sri_kf2_user_pct", "sri_kf3_grid_pct", "sbp_level"]


def layout(**_):
    opts = building_options()
    default = [o["value"] for o in opts[:3]]
    return html.Div([
        html.Div(className="page-head", children=[
            html.H1("Compare smartness level of buildings"),
            html.P(f"Select 2 to {MAX_BUILDINGS} buildings to compare their smartness profiles."),
        ]),
        card(control("Buildings", dcc.Dropdown(id="cmp-select", options=opts, value=default, multi=True))),
        html.Div(id="cmp-warning", className="muted"),
        card(html.Div(id="cmp-table"), title="Key figures"),
        html.Div(className="grid-2", children=[
            card(dcc.Graph(id="cmp-kf", config=GRAPH_CONFIG)),
            card(dcc.Graph(id="cmp-sbp", config=GRAPH_CONFIG)),
        ]),
        html.Div(className="grid-2", children=[
            card(dcc.Graph(id="cmp-impacts", config=GRAPH_CONFIG)),
            card(dcc.Graph(id="cmp-domains", config=GRAPH_CONFIG)),
        ]),
    ])


@callback(
    Output("cmp-table", "children"), Output("cmp-kf", "figure"), Output("cmp-sbp", "figure"),
    Output("cmp-impacts", "figure"), Output("cmp-domains", "figure"), Output("cmp-warning", "children"),
    Input("cmp-select", "value"),
)
def _compare(ids):
    ids = (ids or [])[:MAX_BUILDINGS]
    b = get_data().buildings
    d = b.set_index("building_id").loc[[i for i in ids if i in set(b["building_id"])]].reset_index()
    warn = ""
    if len(ids) < 2:
        warn = "Select at least two buildings."
    elif d.reindex(columns=IMPACT_COLS).isna().all(axis=1).any():
        warn = "Some selected buildings have no impact/domain detail; they are omitted from those charts."

    header = html.Tr([html.Th("")] + [html.Th(r["short_name"]) for _, r in d.iterrows()])
    body = [html.Tr([html.Th(label(c, with_unit=False))] + [html.Td(fmt(c, r[c])) for _, r in d.iterrows()])
            for c in TABLE_FIELDS if c in d.columns]
    table = html.Table([header] + body, className="info-table compare-table")

    return (
        table,
        radar(d, KF_COLS, "SRI key functionalities [%]"),
        radar(d, SBP_TOPIC_COLS, "Smart by Powerhouse topic levels (−2 … 4)", rng=(-2, 4)),
        radar(d, IMPACT_COLS, "SRI impact criteria [%]"),
        grouped_bars(d, DOMAIN_COLS, "SRI technical domains [%]", rng=[-50, 100]),
        warn,
    )
