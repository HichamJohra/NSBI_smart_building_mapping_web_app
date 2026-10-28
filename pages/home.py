"""Main dashboard: filters, bubble map, statistics, XY correlation plot and full dataset table."""
import dash
import dash_ag_grid as dag
import numpy as np
import pandas as pd
from dash import ALL, MATCH, Input, Output, Patch, State, callback, ctx, dcc, html, no_update

from components.data import columns_for, dropdown_options, fmt, get_data, is_numeric, label, unit
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
DEFAULT_CAT_FILTER = "source_study"          # parameter pre-selected in the first category filter
STAT_DEFAULTS = ["sri_total_pct", "sbp_level"]  # parameters pre-selected in the two statistics cards
HIDDEN = {"display": "none"}


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


# ----------------------------------------------------------------- dynamic filter rows
def _cat_row(index: int, param: str | None = None) -> html.Div:
    """One category filter: parameter dropdown + values dropdown + remove button."""
    cols = columns_for("filter", "categorical")
    param = param if param in cols else None
    return html.Div(id={"type": "catf-row", "index": index}, className="filter-row", children=[
        dcc.Dropdown(id={"type": "catf-param", "index": index}, options=dropdown_options(cols), value=param,
                     placeholder="Choose a category parameter…"),
        dcc.Dropdown(id={"type": "catf-vals", "index": index}, options=_cat_values(param), value=[], multi=True,
                     placeholder="All values"),
        html.Button("✕", id={"type": "catf-del", "index": index}, className="btn-icon", title="Remove this filter"),
    ])


def _num_row(index: int, param: str | None = None) -> html.Div:
    """One numeric filter: parameter dropdown + range slider + remove button."""
    cols = columns_for("filter", "numeric")
    param = param if param in cols else None
    lo, hi, val, marks, step, disabled = _range_config(param)
    return html.Div(id={"type": "numf-row", "index": index}, className="filter-row", children=[
        dcc.Dropdown(id={"type": "numf-param", "index": index}, options=dropdown_options(cols), value=param,
                     placeholder="Choose a numeric parameter…"),
        html.Div(className="range-block", children=dcc.RangeSlider(
            id={"type": "numf-range", "index": index}, min=lo, max=hi, value=val, marks=marks, step=step,
            disabled=disabled, tooltip={"placement": "bottom", "always_visible": True})),
        html.Button("✕", id={"type": "numf-del", "index": index}, className="btn-icon", title="Remove this filter"),
    ])


def _stat_card(index: int, param: str | None) -> html.Div:
    cols = columns_for("xy", "numeric")
    return html.Div(className="stat-card", children=[
        control("Statistics for", dcc.Dropdown(id={"type": "stat-param", "index": index},
                                               options=dropdown_options(cols), value=_pick(param, cols, index),
                                               clearable=False)),
        html.Div(id={"type": "stat-out", "index": index}),
    ])


def layout(**_):
    data = get_data()
    b = data.buildings
    size_cols = columns_for("map_size", "numeric")
    color_cols = columns_for("map_color")
    xy_cols = columns_for("xy", "numeric")

    filters = card(
        [
            html.Div(className="grid-2 filters-grid", children=[
                html.Div([
                    html.Label("Category filters", className="control-label"),
                    html.Div(id="db-catf-list", children=[_cat_row(0, DEFAULT_CAT_FILTER)]),
                    html.Button("+ Add category filter", id="db-catf-add", className="btn-light"),
                ]),
                html.Div([
                    html.Label("Numeric filters", className="control-label"),
                    html.Div(id="db-numf-list", children=[_num_row(0)]),
                    html.Button("+ Add numeric filter", id="db-numf-add", className="btn-light"),
                ]),
            ]),
            html.Div(className="filter-footer", children=[
                html.Span(id="db-filter-count", className="muted"),
                html.Button("Reset filters", id="db-reset", className="btn"),
            ]),
        ],
        title="Filters",
        subtitle="Filters apply to the map, the statistics, the correlation plot and the table. All filters are "
                 "combined (AND). Buildings without a value for a numeric filter parameter are excluded while "
                 "that filter is active.",
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
                control("Map background", dcc.Dropdown(id="db-basemap", options=BASEMAPS, value="carto-positron",
                                                       clearable=False)),
            ]),
            graph("db-map"),
            html.Div(id="db-selected", className="selected-panel",
                     children="Click a bubble (map or plot) to open the building's detail page."),
            html.Div(className="grid-2 stat-row", children=[_stat_card(i, p) for i, p in enumerate(STAT_DEFAULTS)]),
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
            html.H1("Smart buildings in the World"),
            html.P("Smartness, performance, and characteristics of real buildings."),
        ]),
        html.Div(className="kpi-row", children=[
            kpi("Buildings shown", "db-kpi-n"),
            kpi("Total surface area", "db-kpi-area", "db-kpi-area-sub"),
            kpi("Countries", "db-kpi-countries"),
            kpi("Municipalities", "db-kpi-mun"),
        ]),
        filters,
        map_card,
        scatter_card,
        table_card,
        dcc.Store(id="db-ids"),
    ])


# ----------------------------------------------------------------- callbacks: filter rows
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


def _edit_rows(row_ids, make_row):
    """Shared add/remove logic for the two filter lists (keeps at least one row)."""
    trig = ctx.triggered_id
    if not ctx.triggered or not ctx.triggered[0]["value"]:
        return no_update  # a new remove button appeared (n_clicks None), not a click
    indices = [r["index"] for r in row_ids]
    p = Patch()
    if isinstance(trig, str):  # "+ Add" button
        p.append(make_row(max(indices, default=-1) + 1))
        return p
    if len(indices) <= 1 or trig["index"] not in indices:
        return no_update
    del p[indices.index(trig["index"])]
    return p


@callback(
    Output("db-catf-list", "children"),
    Input("db-catf-add", "n_clicks"), Input({"type": "catf-del", "index": ALL}, "n_clicks"),
    State({"type": "catf-row", "index": ALL}, "id"), prevent_initial_call=True,
)
def _edit_cat_filters(_add, _dels, row_ids):
    return _edit_rows(row_ids, _cat_row)


@callback(
    Output("db-numf-list", "children"),
    Input("db-numf-add", "n_clicks"), Input({"type": "numf-del", "index": ALL}, "n_clicks"),
    State({"type": "numf-row", "index": ALL}, "id"), prevent_initial_call=True,
)
def _edit_num_filters(_add, _dels, row_ids):
    return _edit_rows(row_ids, _num_row)


@callback(Output({"type": "catf-del", "index": ALL}, "style"), Input({"type": "catf-row", "index": ALL}, "id"))
def _cat_del_visibility(row_ids):
    return [HIDDEN if len(row_ids) <= 1 else {} for _ in row_ids]


@callback(Output({"type": "numf-del", "index": ALL}, "style"), Input({"type": "numf-row", "index": ALL}, "id"))
def _num_del_visibility(row_ids):
    return [HIDDEN if len(row_ids) <= 1 else {} for _ in row_ids]


@callback(
    Output({"type": "catf-vals", "index": MATCH}, "options"), Output({"type": "catf-vals", "index": MATCH}, "value"),
    Input({"type": "catf-param", "index": MATCH}, "value"), prevent_initial_call=True,
)
def _cat_options(col):
    return _cat_values(col), []


@callback(
    Output({"type": "numf-range", "index": MATCH}, "min"), Output({"type": "numf-range", "index": MATCH}, "max"),
    Output({"type": "numf-range", "index": MATCH}, "value"), Output({"type": "numf-range", "index": MATCH}, "marks"),
    Output({"type": "numf-range", "index": MATCH}, "step"), Output({"type": "numf-range", "index": MATCH}, "disabled"),
    Input({"type": "numf-param", "index": MATCH}, "value"), prevent_initial_call=True,
)
def _cfg_range(col):
    return _range_config(col)


@callback(
    Output("db-catf-list", "children", allow_duplicate=True),
    Output("db-numf-list", "children", allow_duplicate=True),
    Output("db-search", "value"),
    Input("db-reset", "n_clicks"), prevent_initial_call=True,
)
def _reset(n):
    base = (n or 0) * 1000  # fresh ids so no stale component state is reused
    return [_cat_row(base, DEFAULT_CAT_FILTER)], [_num_row(base)], ""


@callback(
    Output("db-ids", "data"), Output("db-filter-count", "children"),
    Input({"type": "catf-param", "index": ALL}, "value"), Input({"type": "catf-vals", "index": ALL}, "value"),
    Input({"type": "numf-param", "index": ALL}, "value"), Input({"type": "numf-range", "index": ALL}, "value"),
)
def _filter(cat_params, cat_vals, num_params, num_ranges):
    b = get_data().buildings
    m = pd.Series(True, index=b.index)
    for col, vals in zip(cat_params, cat_vals):
        if col and vals and col in b.columns:
            m &= b[col].astype(str).isin(vals)
    n_active = sum(1 for c, v in zip(cat_params, cat_vals) if c and v)
    for col, rng in zip(num_params, num_ranges):
        if col and rng and col in b.columns:
            m &= b[col].astype(float).between(rng[0] - 1e-9, rng[1] + 1e-9)
            n_active += 1
    ids = b.loc[m, "building_id"].tolist()
    return ids, f"{len(ids)} of {len(b)} buildings match · {n_active} active filter(s)"


# ----------------------------------------------------------------- callbacks: views
def _subset(ids):
    b = get_data().buildings
    return b if ids is None else b[b["building_id"].isin(ids)]


@callback(
    Output("db-kpi-n", "children"), Output("db-kpi-area", "children"), Output("db-kpi-area-sub", "children"),
    Output("db-kpi-countries", "children"), Output("db-kpi-mun", "children"),
    Input("db-ids", "data"),
)
def _kpis(ids):
    d = _subset(ids)
    if "floor_area_m2" in d and d["floor_area_m2"].notna().any():
        known = d["floor_area_m2"].dropna()
        area = fmt("floor_area_m2", float(known.sum()))
        area_sub = f"{len(known)} of {len(d)} buildings with known floor area"
    else:
        area, area_sub = "–", "no floor area data for these buildings"
    countries = d["country"].nunique() if "country" in d else "–"
    mun = d["municipality"].nunique() if "municipality" in d else "–"
    return f"{len(d)}", area, area_sub, f"{countries}", f"{mun}"


@callback(
    Output({"type": "stat-out", "index": MATCH}, "children"),
    Input({"type": "stat-param", "index": MATCH}, "value"), Input("db-ids", "data"),
)
def _stat(col, ids):
    d = _subset(ids)
    if not col or col not in d:
        return html.Div("Choose a parameter", className="muted")
    v = d[col].dropna().astype(float)
    if v.empty:
        return html.Div("No values for the filtered buildings", className="muted")
    std = fmt(col, float(v.std(ddof=1))) if len(v) > 1 else "n/a"
    return html.Div([
        html.Div([html.Span(fmt(col, float(v.mean())), className="stat-main"),
                  html.Span(f" ± {std}", className="stat-std")]),
        html.Div("mean ± standard deviation", className="muted"),
        html.Div(f"n = {len(v)} of {len(d)} buildings · min {fmt(col, float(v.min()))} · max {fmt(col, float(v.max()))}",
                 className="muted"),
    ])


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
