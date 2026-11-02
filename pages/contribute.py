"""Contribute data page: send a building through an online form, or fill in and upload the Excel template.

Submissions are validated, checked against bots, and stored as Excel files (components/submissions.py).
They are reviewed by the maintainer before anything is added to the published dataset.
"""
from typing import Any

import dash
from dash import ALL, Input, Output, State, callback, ctx, dcc, html, no_update

from components import submissions as sub
from components.data import all_columns, get_data, is_numeric, label, tooltip, unit
from components.ui import card

dash.register_page(__name__, path="/contribute", name="Contribute data", order=3,
                   title="Contribute data · NSBI Smart Buildings")

TEXTAREA_COLUMNS = {"notes"}
CONSENT_OPTIONS: Any = [{"label": " I confirm that the data can be published in the NSBI dataset with the "
                                  "reference(s) given, and that it contains no personal data.", "value": "ok"}]
UPLOAD_STYLE: Any = {"borderStyle": "dashed"}


# ----------------------------------------------------------------- form fields
def _field(col: str) -> html.Div:
    """Label + input for one parameter. Categorical fields suggest the values already in the dataset."""
    fid: Any = {"type": "sub-field", "col": col}
    req = col in sub.REQUIRED
    head = html.Label([label(col, with_unit=False), html.Span(" *", className="req") if req else None],
                      title=tooltip(col), className="control-label")
    u = unit(col)
    hint_parts = [u] if u else []
    rng = sub.value_range(col)
    if rng and is_numeric(col):
        hint_parts.append(f"{rng[0]:g} … {'∞' if rng[1] == float('inf') else f'{rng[1]:g}'}")
    hint = html.Div(" · ".join(hint_parts), className="field-hint") if hint_parts else None
    if is_numeric(col):
        inp = dcc.Input(id=fid, type="number", step="any", className="field-input", debounce=True)
        return html.Div([head, inp, hint], className="sub-field")
    if col in TEXTAREA_COLUMNS:
        return html.Div([head, dcc.Textarea(id=fid, className="field-input field-area"), hint],
                        className="sub-field sub-field-wide")
    values = get_data().buildings[col].dropna().astype(str).unique() if col in get_data().buildings.columns else []
    dl_id = f"sub-dl-{col}"
    inp = dcc.Input(id=fid, type="text", list=dl_id, className="field-input", debounce=True,
                    placeholder="Type or choose…" if len(values) else "")
    return html.Div([head, inp, html.Datalist(id=dl_id, children=[html.Option(value=v) for v in sorted(values)]),
                     hint], className="sub-field")


def _form() -> html.Div:
    d = get_data().dictionary
    cols = sub.contributed_columns()
    groups = list(dict.fromkeys(g for c, g in zip(d["column"], d["group"]) if c in cols and g))
    sections: list = [
        html.H4("Required information"),
        html.Div([_field(c) for c in sub.REQUIRED if c in cols], className="field-grid"),
        html.P("Plus at least one result below: an SRI score, a Smart by Powerhouse level or a building "
               "performance indicator. Fill in what you know; leave the rest empty.", className="muted"),
    ]
    for g in groups:
        gcols = [c for c, gg in zip(d["column"], d["group"]) if gg == g and c in cols and c not in sub.REQUIRED]
        if gcols:
            sections.append(html.Details(className="var-group", children=[
                html.Summary(f"{g} ({len(gcols)} field{'s' if len(gcols) != 1 else ''})"),
                html.Div([_field(c) for c in gcols], className="field-grid"),
            ]))
    undocumented = [c for c in cols if c not in set(d["column"])]
    if undocumented:
        sections.append(html.Details(className="var-group", children=[
            html.Summary("Other"), html.Div([_field(c) for c in undocumented], className="field-grid")]))
    return html.Div(sections)


def _upload_tab() -> html.Div:
    return html.Div([
        html.H4("1. Download the template"),
        html.P("The template has one column per parameter (row 1, do not change it), a 'data_dictionary' sheet "
               "explaining every column and its unit, and short instructions. One row per building."),
        html.Button("Download the Excel template", id="sub-template-btn", className="btn"),
        dcc.Download(id="sub-template-dl"),
        html.H4("2. Upload the filled-in file"),
        dcc.Upload(id="sub-upload", accept=".xlsx", max_size=sub.MAX_UPLOAD_BYTES, multiple=False,
                   className="upload-box", style=UPLOAD_STYLE,
                   children=html.Div(["Drag and drop the Excel file here, or ", html.A("choose a file"),
                                      html.Div(f"(.xlsx, max {sub.MAX_UPLOAD_MB:g} MB, "
                                               f"max {sub.MAX_ROWS_PER_UPLOAD} buildings)", className="muted")])),
        html.Div(id="sub-upload-report", className="upload-report"),
    ])


def layout(**_):
    question, token = sub.new_challenge()
    return html.Div([
        html.Div(className="page-head", children=[
            html.H1("Contribute data"),
            html.P("Share the smartness and performance data of a building to enrich the NSBI dataset."),
        ]),
        card([
            html.P(["You can send ", html.B("one building with the online form"), ", or ",
                    html.B("one or several buildings with the Excel template"), ". Every entry is checked "
                    "automatically and then reviewed by the NSBI team before it is added to the published dataset."]),
            html.P(["Hover a field name for its definition. ", html.B("Do not enter personal data"),
                    " (names, e-mail addresses, phone numbers): this page does not collect any, and anonymised "
                    "building names are fine."], className="muted"),
        ], title="How it works"),
        dcc.Tabs(id="sub-tabs", value="form", className="sub-tabs", children=[
            dcc.Tab(label="Online form (one building)", value="form", children=card(_form())),
            dcc.Tab(label="Excel template (one or several buildings)", value="upload", children=card(_upload_tab())),
        ]),
        card([
            html.Div(className="grid-2", children=[
                html.Div([
                    html.Label("Comment to the NSBI team (optional, no personal data)", className="control-label"),
                    dcc.Textarea(id="sub-comment", className="field-input field-area", maxLength=sub.MAX_TEXT_LENGTH),
                ]),
                html.Div([
                    html.Label(["Anti-spam check: ", html.Span(question, id="sub-question")],
                               className="control-label"),
                    dcc.Input(id="sub-human", type="number", className="field-input", placeholder="Answer"),
                    dcc.Checklist(id="sub-consent", options=CONSENT_OPTIONS, value=[], className="consent"),
                ]),
            ]),
            # Honeypot: invisible to people, often filled in by bots
            html.Div(className="hp-field", **{"aria-hidden": "true"}, children=[
                html.Label("Leave this field empty", htmlFor="sub-website"),
                dcc.Input(id="sub-website", type="text", autoComplete="off"),
            ]),
            html.Div(className="filter-footer", children=[
                html.Span("The content of the selected tab (form or uploaded file) is sent.", className="muted"),
                html.Button("Send", id="sub-send", className="btn"),
            ]),
            dcc.Loading(html.Div(id="sub-result"), type="dot"),
        ], title="Send"),
        dcc.Store(id="sub-token", data=token),
    ])


# ----------------------------------------------------------------- callbacks
@callback(Output("sub-template-dl", "data"), Input("sub-template-btn", "n_clicks"), prevent_initial_call=True)
def _download_template(_):
    return dcc.send_bytes(sub.template_bytes(), "NSBI_data_contribution_template.xlsx")


def _messages(errors: list[str], max_n: int = 30) -> html.Ul:
    items = [html.Li(e) for e in errors[:max_n]]
    if len(errors) > max_n:
        items.append(html.Li(f"… and {len(errors) - max_n} more."))
    return html.Ul(items)


@callback(Output("sub-upload-report", "children"), Input("sub-upload", "contents"), State("sub-upload", "filename"),
          prevent_initial_call=True)
def _check_upload(contents, filename):
    if not contents:
        return ""
    records, errors = sub.parse_upload(contents, filename)
    if errors:
        return html.Div([html.B(f"{filename}: please correct the following and upload again:"), _messages(errors)],
                        className="msg msg-error")
    names = ", ".join(str(r.get("building_name")) for r in records[:5]) + (" …" if len(records) > 5 else "")
    return html.Div([html.B(f"{filename}: {len(records)} building(s) ready to send"), html.Div(names)],
                    className="msg msg-ok")


@callback(
    Output("sub-result", "children"), Output("sub-question", "children"), Output("sub-token", "data"),
    Output("sub-human", "value"),
    Input("sub-send", "n_clicks"),
    State("sub-tabs", "value"), State({"type": "sub-field", "col": ALL}, "value"),
    State("sub-upload", "contents"), State("sub-upload", "filename"),
    State("sub-comment", "value"), State("sub-consent", "value"),
    State("sub-human", "value"), State("sub-website", "value"), State("sub-token", "data"),
    prevent_initial_call=True,
)
def _send(_, tab, field_values, contents, filename, comment, consent, answer, honeypot, token):
    """Validate, run the anti-spam checks and store the submission."""
    question, new_token = sub.new_challenge()  # a fresh question after every attempt
    fresh = (question, new_token, None)

    def fail(msgs):
        return (html.Div([html.B("Not sent:"), _messages(msgs)], className="msg msg-error"), *fresh)

    human = sub.check_human(token, answer, honeypot)
    if human == "bot":  # honeypot filled in: pretend success, store nothing
        return (html.Div("Thank you, your data has been received.", className="msg msg-ok"), *fresh)
    if human:
        return fail([human])
    if "ok" not in (consent or []):
        return fail(["Please tick the confirmation box."])
    if sub.rate_limited(sub.client_id()):
        return fail(["Too many submissions from your connection. Please try again later."])

    if tab == "upload":
        if not contents:
            return fail(["Upload a filled-in template first (step 2)."])
        records, errors = sub.parse_upload(contents, filename)
        kind = "upload"
    else:
        ids = [s["id"]["col"] for s in ctx.states_list[1]]
        raw = dict(zip(ids, field_values))
        record, errors = sub.clean_record(raw)
        records, kind, filename = [record], "form", ""
    if errors:
        return fail(errors)
    try:
        sub_id = sub.save_submission(records, kind, comment=comment or "", original_filename=filename or "")
    except OSError:
        return fail(["The submission could not be stored on the server. Please try again later."])
    return (html.Div([html.B("Thank you! Your data has been received."),
                      html.Div(f"{len(records)} building(s) · reference {sub_id}. It will be reviewed before "
                               "publication.")], className="msg msg-ok"), *fresh)
