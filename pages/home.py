"""Main dashboard: filters, bubble map, XY correlation plot and full dataset table."""
import dash
import dash_ag_grid as dag
import numpy as np
import pandas as pd
from dash import Input, Output, Patch, callback, ctx, dcc, html, no_update

from components.data import columns_for, dropdown_options, get_data, is_numeric, label, unit
from components.figures import map_figure, scatter_figure
from components.ui import card, control, graph, kpi

dash.register_page(__name__, path="/", name="Dashboard", order=0, title="Dashboard · NSBI Smart Buildings")

BASEMAPS = [
    {"label": "Light (Carto Positron)", "value": "carto-positron"},
    {"label": "OpenStreetMap", "value": "open-street-map"},
    {"label": "Carto Voyager", "value": "carto-voyager"},
    {"label": "Dark", "value": "carto-darkmatter"},
]
COLORSCALES = ["Viridis", "RdYlGn", "Plasma", "Blues", "Turbo"]


def _pick(preferred: str, options: list[str], fallback_index: int = 0):
    if preferred in options:
        return preferred
    return options[fallback_index] if len(options) > fallback_index else (options[0] if options else None)


def _cat_values(col: str | None) -> list[dict]:
    if not col:
        return []
    vals = get_data().buildings[col].dropna().astype(str).unique()
    return [{"label": v, "value": v} for v in sorted(vals)]


def _column_defs(df: pd.DataFrame) -> list[dict]:
    order = [c for c in get_data().dictionary["column"] if c in df.columns]
    order += [c for c in df.columns if c not in order]
    defs = []
    for c in order:
        d = {"field": c, "headerName": label(c), "headerTooltip": label(c), "minWidth": 120}
        if is_numeric(c):
            d["filter"] = "agNumberColumnFilter"
            if unit(c) in ("%",) or unit(c).startswith("level"):
                d["valueFormatter"] = {"function": "params.value == null ? '' : d3.format('.2~f')(params.value)"}
        else:
            d["filter"] = "agTextColumnFilter"
        if c == "short_name":
            d.update(pinned="left", minWidth=130)
        defs.append(d)
    return defs


def layout(**_):
    data = get_data()
    b = data.buildings
    size_cols = columns_for("map_size", "numeric")
    color_cols = columns_for("map_color")
    xy_cols = columns_for("xy", "numeric")
    num_filter_cols = columns_for("filter", "numeric")
    cat_filter_cols = columns_for("filter", "categorical")

    filters = card(
        [
            html.Div(className="grid-4", children=[
                control("Source study", dcc.Dropdown(id="db-f-source", options=_cat_values("source_study") if "source_study" in b else [],
                                                     multi=True, placeholder="All")),
                control("Building category", dcc.Dropdown(id="db-f-category", options=_cat_values("building_category") if "building_category" in b else [],
                                                          multi=True, placeholder="All")),
                control("Other category filter", dcc.Dropdown(id="db-f-catparam", options=dropdown_options(cat_filter_cols),
                                                              placeholder="Choose a parameter…")),
                control("…values", dcc.Dropdown(id="db-f-catvals", multi=True, placeholder="All")),
            ]),
            html.Div(className="grid-2", children=[
                html.Div([
                    control("Numeric filter 1", dcc.Dropdown(id="db-f-num1", options=dropdown_options(num_filter_cols),
                                                             placeholder="Choose a parameter…")),
                    dcc.RangeSlider(id="db-f-range1", min=0, max=1, value=[0, 1], disabled=True,
                                    tooltip={"placement": "bottom", "always_visible": True}),
                ], className="range-block"),
                html.Div([
                    control("Numeric filter 2", dcc.Dropdown(id="db-f-num2", options=dropdown_options(num_filter_cols),
                                                             placeholder="Choose a parameter…")),
                    dcc.RangeSlider(id="db-f-range2", min=0, max=1, value=[0, 1], disabled=True,
                                    tooltip={"placement": "bottom", "always_visible": True}),
                ], className="range-block"),
            ]),
            html.Div(className="filter-footer", children=[
                html.Span(id="db-filter-count", className="muted"),
                html.Button("Reset filters", id="db-reset", className="btn"),
            ]),
        ],
        title="Filters", subtitle="Filters apply to the map, the correlation plot and the table. "
                                  "Buildings without a value for a numeric filter parameter are excluded while that filter is active.",
    )

    map_card = card(
        [
            html.Div(className="grid-4", children=[
                control("Bubble size", dcc.Dropdown(id="db-size", options=dropdown_options(size_cols),
                                                    value=_pick("sri_total_pct", size_cols), clearable=True,
                                                    placeholder="Same size")),
                control("Bubble colour", dcc.Dropdown(id="db-color", options=dropdown_options(color_cols),
                                                      value=_pick("sbp_level", color_cols), clearable=True,
                                                      placeholder="Single colour")),
                control("Colour scale (numeric)", dcc.Dropdown(id="db-cscale", options=COLORSCALES, value="Viridis",
                                                               clearable=False)),
                control("Base map", dcc.Dropdown(id="db-basemap", options=BASEMAPS, value="carto-positron",
                                                 clearable=False)),
            ]),
            graph("db-map"),
            html.Div(id="db-selected", className="selected-panel",
                     children="Click a bubble (map or plot) to open the building's detail page."),
        ],
        title="Map of smart buildings",
        subtitle="Bubble size and colour show the selected parameters. Hover for details; scroll to zoom.",
    )

    scatter_card = card(
        [
            html.Div(className="grid-4", children=[
                control("X axis", dcc.Dropdown(id="db-x", options=dropdown_options(xy_cols),
                                               value=_pick("sri_total_pct", xy_cols), clearable=False)),
                control("Y axis", dcc.Dropdown(id="db-y", options=dropdown_options(xy_cols),
                                               value=_pick("sbp_level", xy_cols, 1), clearable=False)),
                control("Colour by", dcc.Dropdown(id="db-xy-color", options=dropdown_options(color_cols),
                                                  value=_pick("source_study", color_cols), clearable=True,
                                                  placeholder="Single colour")),
                control("Options", dcc.Checklist(id="db-xy-opts", options=[
                    {"label": " Linear fit", "value": "trend"}, {"label": " Labels", "value": "labels"}],
                    value=["trend", "labels"], inline=True, className="checklist")),
            ]),
            graph("db-scatter"),
            html.Div(id="db-stats", className="stats"),
        ],
        title="Correlation explorer",
        subtitle="Choose any two parameters to plot against each other. Statistics are computed on the filtered buildings.",
    )

    table_card = card(
        [
            html.Div(className="table-toolbar", children=[
                dcc.Input(id="db-search", type="search", placeholder="Search all columns…", debounce=False,
                          className="search"),
                html.Button("Export CSV", id="db-export", className="btn"),
            ]),
            dag.AgGrid(
                id="db-grid",
                rowData=[],
                columnDefs=_column_defs(b),
                defaultColDef={"sortable": True, "filter": True, "floatingFilter": True, "resizable": True},
                dashGridOptions={"pagination": True, "paginationPageSize": 20, "enableCellTextSelection": True,
                                 "tooltipShowDelay": 300},
                csvExportParams={"fileName": "nsbi_smart_buildings.csv"},
                style={"height": "560px", "width": "100%"},
            ),
        ],
        title="Full dataset",
        subtitle="Sort and filter each column from its header, or search across all columns. Scroll sideways for all parameters.",
    )

    return html.Div([
        html.Div(className="page-head", children=[
            html.H1("Smart buildings in Norway"),
            html.P("Smart Readiness Indicator (SRI) and Smart by Powerhouse (SbP) assessments of real buildings."),
        ]),
        html.Div(className="kpi-row", children=[
            kpi("Buildings shown", "db-kpi-n"),
            kpi("Mean SRI score", "db-kpi-sri"),
            kpi("Mean SbP level", "db-kpi-sbp"),
            kpi("Municipalities", "db-kpi-mun"),
        ]),
        filters,
        map_card,
        scatter_card,
        table_card,
        dcc.Store(id="db-ids"),
    ])


# ----------------------------------------------------------------- callbacks
def _range_config(col):
    if not col:
        return 0, 1, [0, 1], None, None, True
    s = get_data().buildings[col].dropna().astype(float)
    if s.empty:
        return 0, 1, [0, 1], None, None, True
    lo, hi = float(np.floor(s.min() * 100) / 100), float(np.ceil(s.max() * 100) / 100)
    if lo == hi:
        hi = lo + 1
    step = 1 if (s % 1 == 0).all() and (hi - lo) >= 5 else float(10 ** np.floor(np.log10((hi - lo) / 100)))
    marks = {lo: f"{lo:g}", hi: f"{hi:g}"}
    return lo, hi, [lo, hi], marks, step, False


@callback(
    Output("db-f-range1", "min"), Output("db-f-range1", "max"), Output("db-f-range1", "value"),
    Output("db-f-range1", "marks"), Output("db-f-range1", "step"), Output("db-f-range1", "disabled"),
    Input("db-f-num1", "value"),
)
def _cfg_range1(col):
    return _range_config(col)


@callback(
    Output("db-f-range2", "min"), Output("db-f-range2", "max"), Output("db-f-range2", "value"),
    Output("db-f-range2", "marks"), Output("db-f-range2", "step"), Output("db-f-range2", "disabled"),
    Input("db-f-num2", "value"),
)
def _cfg_range2(col):
    return _range_config(col)


@callback(Output("db-f-catvals", "options"), Output("db-f-catvals", "value"), Input("db-f-catparam", "value"))
def _cat_options(col):
    return _cat_values(col), []


@callback(
    Output("db-f-source", "value"), Output("db-f-category", "value"), Output("db-f-catparam", "value"),
    Output("db-f-num1", "value"), Output("db-f-num2", "value"), Output("db-search", "value"),
    Input("db-reset", "n_clicks"), prevent_initial_call=True,
)
def _reset(_):
    return [], [], None, None, None, ""


@callback(
    Output("db-ids", "data"), Output("db-filter-count", "children"),
    Input("db-f-source", "value"), Input("db-f-category", "value"),
    Input("db-f-catparam", "value"), Input("db-f-catvals", "value"),
    Input("db-f-num1", "value"), Input("db-f-range1", "value"),
    Input("db-f-num2", "value"), Input("db-f-range2", "value"),
)
def _filter(sources, cats, catparam, catvals, num1, rng1, num2, rng2):
    b = get_data().buildings
    m = pd.Series(True, index=b.index)
    if sources:
        m &= b["source_study"].astype(str).isin(sources)
    if cats:
        m &= b["building_category"].astype(str).isin(cats)
    if catparam and catvals:
        m &= b[catparam].astype(str).isin(catvals)
    for col, rng in ((num1, rng1), (num2, rng2)):
        if col and rng and col in b.columns:
            v = b[col].astype(float)
            m &= v.between(rng[0] - 1e-9, rng[1] + 1e-9)
    ids = b.loc[m, "building_id"].tolist()
    return ids, f"{len(ids)} of {len(b)} buildings match the filters"


def _subset(ids):
    b = get_data().buildings
    return b if ids is None else b[b["building_id"].isin(ids)]


@callback(
    Output("db-kpi-n", "children"), Output("db-kpi-sri", "children"),
    Output("db-kpi-sbp", "children"), Output("db-kpi-mun", "children"),
    Input("db-ids", "data"),
)
def _kpis(ids):
    d = _subset(ids)
    sri = f"{d['sri_total_pct'].mean():.1f} %" if "sri_total_pct" in d and d["sri_total_pct"].notna().any() else "–"
    sbp = f"{d['sbp_level'].mean():.2f}" if "sbp_level" in d and d["sbp_level"].notna().any() else "–"
    mun = d["municipality"].nunique() if "municipality" in d else "–"
    return f"{len(d)}", sri, sbp, f"{mun}"


@callback(
    Output("db-map", "figure"),
    Input("db-ids", "data"), Input("db-size", "value"), Input("db-color", "value"),
    Input("db-basemap", "value"), Input("db-cscale", "value"),
)
def _map(ids, size_col, color_col, basemap, cscale):
    return map_figure(_subset(ids), size_col, color_col, basemap=basemap, colorscale=cscale)


@callback(
    Output("db-scatter", "figure"), Output("db-stats", "children"),
    Input("db-ids", "data"), Input("db-x", "value"), Input("db-y", "value"),
    Input("db-xy-color", "value"), Input("db-xy-opts", "value"),
)
def _scatter(ids, x, y, color, opts):
    opts = opts or []
    fig, stats = scatter_figure(_subset(ids), x, y, color, trendline="trend" in opts, show_labels="labels" in opts)
    return fig, stats


@callback(Output("db-grid", "rowData"), Input("db-ids", "data"))
def _table(ids):
    d = _subset(ids)
    return d.astype(object).where(d.notna(), None).to_dict("records")


@callback(Output("db-grid", "dashGridOptions"), Input("db-search", "value"), prevent_initial_call=True)
def _search(text):
    p = Patch()
    p["quickFilterText"] = text or ""
    return p


@callback(Output("db-grid", "exportDataAsCsv"), Input("db-export", "n_clicks"), prevent_initial_call=True)
def _export(_):
    return True


@callback(
    Output("db-selected", "children"),
    Input("db-map", "clickData"), Input("db-scatter", "clickData"), prevent_initial_call=True,
)
def _select(map_click, scatter_click):
    click = map_click if ctx.triggered_id == "db-map" else scatter_click
    try:
        bid = click["points"][0]["customdata"]
    except (TypeError, KeyError, IndexError):
        return no_update
    if isinstance(bid, list):
        bid = bid[0]
    b = get_data().buildings
    row = b[b["building_id"] == bid]
    if row.empty:
        return no_update
    r = row.iloc[0]
    return html.Span([
        html.B(r["building_name"]), f" — {r.get('city', '')}  ",
        dcc.Link("Open building details →", href=f"/building?building_id={bid}", className="link-strong"),
    ])
