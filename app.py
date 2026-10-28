"""NSBI Smart Building Mapping — multi-page Dash web app.

Run locally:  python app.py   ->  http://127.0.0.1:8050
"""
import dash
from dash import Dash, dcc, html

app = Dash(
    __name__,
    use_pages=True,  # every module in ./pages registering itself becomes a page
    title="NSBI Smart Buildings",
    suppress_callback_exceptions=True,
)
server = app.server  # WSGI entry point for later deployment (gunicorn app:server)


def navbar() -> html.Header:
    links = [
        dcc.Link(page["name"], href=page["relative_path"], className="nav-link")
        for page in dash.page_registry.values()
    ]
    return html.Header(
        className="navbar",
        children=[html.Div("NSBI Smart Building Mapping", className="brand"), html.Nav(links)],
    )


app.layout = html.Div([navbar(), html.Main(dash.page_container, className="container")])


if __name__ == "__main__":
    app.run(debug=True)
