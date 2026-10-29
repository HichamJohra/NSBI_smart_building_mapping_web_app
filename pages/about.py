"""About / methodology page: frameworks, scales, data sources and caveats."""
import dash
from dash import dcc, html

from components.data import SBP_LEVEL_NAMES, get_data
from components.ui import card

dash.register_page(__name__, path="/about", name="About", order=99, title="About · NSBI Smart Buildings")

REPOSITORY_URL = "https://github.com/HichamJohra/NSBI_smart_building_mapping_web_app"
CONTACT_NAME, CONTACT_EMAIL = "Hicham Johra", "hicham.johra@sintef.no"

SRI_CLASSES = [("Class 1", "90–100 %"), ("Class 2", "80–90 %"), ("Class 3", "65–80 %"), ("Class 4", "50–65 %"),
               ("Class 5", "35–50 %"), ("Class 6", "20–35 %"), ("Class 7", "< 20 %")]

SBP_DESCRIPTIONS = {
    4: "Self-learning; uses historical data and machine learning to improve prediction, operation and control. "
       "Interacts with neighbouring buildings and surroundings.",
    3: "Predicts future conditions from direct and indirect data, gives recommendations or adjusts the building.",
    2: "Communicates with users, adapts to their preferences and usage patterns. Open APIs simplify data sharing.",
    1: "Has the technical infrastructure to be upgraded to a higher smart level later. Systems can communicate.",
    0: "Ordinary automated building built according to today's regulations.",
    -1: "Existing building (from 1980, renovated or partially upgraded up to TEK10) with some infrastructure; "
        "separate control systems with no communication between them.",
    -2: "Existing building from 1980 or older with little renovation; no integration of systems or sensors and "
        "little or no monitoring and control.",
}

INTRO = """
This web app maps and compares the **smartness** of real buildings, as assessed with two complementary frameworks:

* **Smart Readiness Indicator (SRI)** – the EU's common scheme for rating how ready a building is to use smart
  technologies. Smart-ready services are scored across **9 technical domains** (heating, domestic hot water,
  cooling, ventilation, lighting, dynamic envelope, electricity, EV charging, monitoring and control) and
  **7 impact criteria**, aggregated into **3 key functionalities**: energy performance and operation (building),
  response to user needs (user) and energy flexibility (grid). The total score is expressed in % and in 7 classes.
* **Smart by Powerhouse (SbP)** – a Norwegian, dialogue-oriented framework describing the ambition/maturity level
  of a building across five topics: enabling technology; indoor climate and working environment; energy and resource
  utilisation; safety, security and reliability; and adaptability. The SINTEF tool implementation used here
  expresses the result on a scale from −2 to 4.
"""

CAVEATS = """
* The EDISON pilots were assessed in February 2026 with the official SRI calculation sheet (v4.5) and cross-checked
  with the U-CERT online tool. The Ålesund buildings (B01–B10) were assessed with **Norway-specific SRI weighting
  factors** (Avendaño et al., 2024), so the two groups are not strictly comparable.
* SRI domains that are not present in a building are shown as *not assessed* (empty), not as 0 %.
  Domain scores can be negative (e.g. EV charging) when a service level penalises the score.
* Map positions flagged *approximate* or *anonymised* are not exact building locations. The Ålesund buildings are
  anonymised in the source and are placed around the city centre.
* Reference years given as a period (e.g. 1960–1990) use the period midpoint for plotting.
* The sample is small: correlations are indicative, not statistically robust.
"""


def _table(header, rows):
    return html.Table([html.Tr([html.Th(h) for h in header])] + [html.Tr([html.Td(c) for c in r]) for r in rows],
                      className="info-table")


def layout(**_):
    src = get_data().sources
    src_rows = []
    for _, r in src.iterrows():
        url = r.get("url")
        ref = html.A(r["reference"], href=url, target="_blank") if isinstance(url, str) and url else r["reference"]
        src_rows.append([r.get("source_id", ""), ref, r.get("used_for", "")])
    return html.Div([
        html.Div(className="page-head", children=[html.H1("About"),
                                                  html.P("Frameworks, scales, data sources and caveats.")]),
        card(dcc.Markdown(INTRO), title="What is shown"),
        html.Div(className="grid-2", children=[
            card(_table(["SRI class", "Total score"], SRI_CLASSES), title="SRI classes"),
            card(_table(["Level", "Name", "Description"],
                        [[f"{k:+d}" if k else "0", SBP_LEVEL_NAMES[k], SBP_DESCRIPTIONS[k]]
                         for k in sorted(SBP_LEVEL_NAMES, reverse=True)]),
                 title="Smart by Powerhouse levels (SINTEF tool implementation)"),
        ]),
        card(dcc.Markdown(CAVEATS), title="Data notes and caveats"),
        card(_table(["ID", "Reference", "Used for"], src_rows), title="Sources"),
        card(dcc.Markdown(
            "The dataset is the Excel file `data/smart_buildings_dataset.xlsx`. Add buildings as new rows in the "
            "`buildings` sheet and new parameters as new columns, registered in the `data_dictionary` sheet "
            "(flags decide in which dropdowns they appear). Refresh the browser to see the changes."),
            title="Updating the data"),
        card([
            html.P(["The data and the code of this web app can be found on GitHub: ",
                    html.A(REPOSITORY_URL, href=REPOSITORY_URL, target="_blank"), "."]),
            html.P(["For comments and suggestions for improvement, contact ", CONTACT_NAME, " (",
                    html.A(CONTACT_EMAIL, href=f"mailto:{CONTACT_EMAIL}"), ")."]),
        ], title="Data, code and contact"),
    ])
