"""NSBI Smart Building Mapping — multipage Dash web app.

Run locally:  python app.py   ->  http://127.0.0.1:8050
"""
import os

import dash
from dash import Dash, dcc, html

app = Dash(
    __name__,
    use_pages=True,  # every module in ./pages registering itself becomes a page
    title="NSBI Smart Buildings",
    suppress_callback_exceptions=True,
)
server = app.server  # WSGI entry point for later deployment (gunicorn app:server)
# Refuse oversized requests before they reach the callbacks (uploads are limited to MAX_UPLOAD_MB on the
# 'Contribute data' page; base64 encoding adds ~35 %).
server.config["MAX_CONTENT_LENGTH"] = int(float(os.environ.get("MAX_UPLOAD_MB", "5")) * 1.5 * 1024 * 1024) + 2 * 1024 * 1024
# The browser-tab icon is assets/favicon.ico (SINTEF), picked up automatically by Dash.

# Partner logos shown at the top right of every page (files in assets/logos/): (file, name, link)
LOGOS = [
    ("logos/sintef_logo.png", "SINTEF Community", "https://www.sintef.no/en/community/"),
    ("logos/ibpsa_nordic_logo.png", "IBPSA Nordic", "https://www.ibpsa-nordic.org/"),
]


def navbar() -> html.Header:
    links = [
        dcc.Link(page["name"], href=page["relative_path"], className="nav-link")
        for page in dash.page_registry.values()
    ]
    logos = [html.A(html.Img(src=app.get_asset_url(path), alt=name, className="nav-logo"),
                    href=url, target="_blank", rel="noopener noreferrer", title=f"{name} – {url}")
             for path, name, url in LOGOS]
    return html.Header(
        className="navbar",
        children=[
            html.Div("NSBI Smart Building Mapping", className="brand"),
            html.Div(className="nav-right", children=[html.Nav(links), html.Div(logos, className="nav-logos")]),
        ],
    )


# Per-tab memory of the dashboard filter rows (the rows are created dynamically, so Dash's built-in
# persistence cannot restore them). storage_type="session" = the browser's sessionStorage: kept while moving
# between pages and on reload, separate for every browser tab and every user, cleared when the tab is closed.
# Simple dropdowns use Dash persistence (components.ui.PERSIST), which uses the same sessionStorage.
app.layout = html.Div([
    dcc.Store(id="mem-db-filters", storage_type="session"),
    navbar(),
    html.Main(dash.page_container, className="container"),
])


if __name__ == "__main__":
    app.run(debug=True)
