"""About / methodology page: frameworks, scales, data sources and caveats."""
import dash
from dash import dcc, html
from dash.development.base_component import Component

from components.data import SBP_LEVEL_NAMES, get_data, label, unit
from components.ui import card

dash.register_page(__name__, path="/about", name="About", order=99, title="About · NSBI Smart Buildings")

SBP_LEVELS_DESC: list[int] = list(range(4, -3, -1))  # SbP levels 4 … −2, highest first

REPOSITORY_URL = "https://github.com/HichamJohra/NSBI_smart_building_mapping_web_app"
NSBI_URL = "https://www.ibpsa-nordic.org/nordic-smart-building-initiative/"
IBPSA_NORDIC_URL = "https://www.ibpsa-nordic.org/"
SINTEF_COMMUNITY_URL = "https://www.sintef.no/en/community/"
CONTACT_NAME, CONTACT_EMAIL = "Hicham Johra", "hicham.johra@sintef.no"
CONTACT_URL = "https://www.sintef.no/en/all-employees/employee/hicham.johra/"

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

# Short explanation of each variable group (keys = 'group' column of the data_dictionary sheet).
# Groups that are not listed here are still shown, without an introduction.
GROUP_INTROS = {
    "Identity": "Who and what the building is: identifiers, names and the owner or project partner.",
    "Location": "Where the building is. Coordinates are used for the map; check the location precision before "
                "reading positions as exact addresses.",
    "Building": "Physical and historical characteristics of the building. The construction or latest renovation "
                "period reflects the age of the technical systems, which strongly influences smart readiness.",
    "Building performance": "Measured, calculated or simulated performance of the building in operation: energy "
                            "use and demand, peak loads, renewable generation and grid exchange, carbon emissions, "
                            "water, envelope U-value, operating cost and occupant satisfaction. Intensities are "
                            "normalized by the conditioned floor area; 'Performance evaluation reference year' tells "
                            "which year the values refer to. Not yet available for the current buildings.",
    "SRI": "Headline Smart Readiness Indicator results. The SRI rates the capability of the technical building "
           "systems (not their measured performance) to use smart technologies, in % of the maximum achievable "
           "for this building, and on a 7-class scale.",
    "SRI key functionality": "The SRI total score is aggregated from three key functionalities. Each one groups "
                             "some of the seven impact criteria below.",
    "SRI impact criteria": "Seven criteria describing what the smart-ready services achieve. Each criterion is "
                           "scored across all technical domains and aggregated with weighting factors that "
                           "depend on the building type and climate.",
    "SRI technical domains": "Nine groups of technical systems in which smart-ready services are assessed. A "
                             "domain absent from the building is not assessed (empty) and does not lower the "
                             "score. The building detail page shows the full domain × impact matrix.",
    "Smart by Powerhouse": "Overall Smart by Powerhouse (SbP) ambition / maturity level, from −2 (no "
                           "technological equipment) to 4 (smart cognitive); see the level table below.",
    "Smart by Powerhouse topics": "SbP assesses functional requirements in five topics. For each topic the "
                                  "dataset gives the level reached (−2 to 4) and the share of available points "
                                  "obtained (%), from which the level is derived.",
    "Metadata": "How and when the assessments were made, and notes on data quality and comparability.",
    "References": "Where the information comes from: a main reference, and separate references for the building "
                  "characteristics and for the performance results (they may be identical).",
}

CAVEATS = """
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


def _variables_section() -> html.Div:
    """All dataset variables, grouped as in the data dictionary, with unit, description and coverage."""
    data = get_data()
    b, d = data.buildings, data.dictionary
    n = len(b)
    groups = list(dict.fromkeys(g for g in d["group"] if g))
    blocks: list[Component] = [html.P(f"The dataset currently contains {n} buildings described by {len(d)} variables, organised "
                     f"in {len(groups)} groups. Hover a variable in any dropdown or table header of the app to "
                     "see the same description. The column name is the name used in the Excel file.")]
    for g in groups:
        rows = d[d["group"] == g]
        table = html.Table(
            [html.Tr([html.Th("Variable"), html.Th("Unit"), html.Th("Description"), html.Th("Available"),
                      html.Th("Column name")])]
            + [html.Tr([
                html.Td(label(c, with_unit=False)),
                html.Td(unit(c) or "–"),
                html.Td(desc),
                html.Td(f"{int(b[c].notna().sum())} / {n}" if c in b.columns else "–"),
                html.Td(html.Code(c)),
            ]) for c, desc in zip(rows["column"], rows["description"])],
            className="info-table vars-table")
        children: list[Component] = [html.Summary(f"{g} ({len(rows)} variable{'s' if len(rows) != 1 else ''})")]
        if GROUP_INTROS.get(g):
            children.append(html.P(GROUP_INTROS[g], className="muted"))
        children.append(table)
        blocks.append(html.Details(open=False, className="var-group", children=children))
    return html.Div(blocks)


def _ext(text: str, url: str) -> html.A:
    return html.A(text, href=url, target="_blank", rel="noopener noreferrer")


def _about_app_section() -> list[Component]:
    """First About card: what the app is, its goal, and the NSBI / IBPSA Nordic / SINTEF context."""
    b = get_data().buildings
    n = len(b)
    n_countries = b["country"].nunique() if "country" in b.columns else 0
    return [
        html.P([
            html.B("NSBI Smart Building Mapping"), " is an open, interactive map and database of real smart "
            "buildings. It brings together, for each documented building, its characteristics, the results of "
            "smartness assessments (e.g., the Smart Readiness Indicator:SRI, Smart by Powerhouse: SbP) and, where "
            "available, indicators of its energy, carbon and operational performance. Users can locate the buildings "
            "on a map, filter and compare them, explore correlations between any two parameters, and look at each "
            "building in detail.",
        ]),
        html.P([
            html.B("Goal: "), "to give researchers, engineers, building owners, practitioners and policy makers a "
            "shared and transparent overview of how smart today's buildings are, starting with the Nordic "
            "countries. The app supports benchmarking of buildings, helps identify where smart solutions would add "
            "most value, and feeds an evidence-based discussion on what makes a building smart and whether smarter "
            f"buildings perform better. The dataset currently contains {n} buildings in {n_countries} "
            f"countr{'y' if n_countries == 1 else 'ies'} and is meant to grow as new cases are documented.",
        ]),
        html.P([
            "The web app is developed within the ", _ext("Nordic Smart Building Initiative (NSBI)", NSBI_URL),
            ", under the umbrella of ", _ext("IBPSA Nordic", IBPSA_NORDIC_URL),
            " (the International Building Performance Simulation Association in the Nordic countries), and is "
            "supported by ", _ext("SINTEF Community", SINTEF_COMMUNITY_URL), " (Norway). NSBI is a collaborative "
            "forum gathering researchers, academics, engineers, consultants and other stakeholders of the smart "
            "building industry in the Nordic and Baltic countries. Through dedicated working groups – one of them "
            "on mapping smart buildings in the Nordics – it investigates key questions on smart buildings and shares "
            "actionable insights with the research community and the building industry.",
        ]),
        html.Div(_ext_img("logos/nsbi_logo.png", "Nordic Smart Building Initiative (NSBI)", NSBI_URL),
                 className="about-logo"),
    ]


def _ext_img(path: str, name: str, url: str) -> html.A:
    return html.A(html.Img(src=dash.get_asset_url(path), alt=name), href=url, target="_blank",
                  rel="noopener noreferrer", title=f"{name} – {url}")


def layout(**_):
    src = get_data().sources
    src_rows = []
    for _, r in src.iterrows():
        url = r.get("url")
        ref = html.A(r["reference"], href=url, target="_blank") if isinstance(url, str) and url else r["reference"]
        src_rows.append([r.get("source_id", ""), ref, r.get("used_for", "")])
    return html.Div([
        html.Div(className="page-head", children=[html.H1("About"),
                                                  html.P("The web app, frameworks, scales, data sources and caveats.")]),
        card(_about_app_section(), title="About this web app"),
        card(dcc.Markdown(INTRO), title="What is shown"),
        card(_variables_section(), title="Dataset variables"),
        html.Div(className="grid-2", children=[
            card(_table(["SRI class", "Total score"], SRI_CLASSES), title="SRI classes"),
            card(_table(["Level", "Name", "Description"],
                        [[f"{k:+d}" if k else "0", SBP_LEVEL_NAMES[k], SBP_DESCRIPTIONS[k]]
                         for k in SBP_LEVELS_DESC]),
                 title="Smart by Powerhouse levels (SINTEF tool implementation)"),
        ]),
        card(dcc.Markdown(CAVEATS), title="Data notes and caveats"),
        card(_table(["ID", "Reference", "Used for"], src_rows), title="Sources"),
        card(dcc.Markdown(
            "The dataset is the Excel file `data/smart_buildings_dataset.xlsx`. Add buildings as new rows in the "
            "`buildings` sheet and new parameters as new columns, registered in the `data_dictionary` sheet "
            "(label, unit, group, type and description). Every parameter then appears automatically in the dropdowns "
            "that fit its type (numeric or category). Refresh the browser to see the changes."),
            title="Updating the data"),
        card([
            html.P(["The data and the code of this web app can be found on GitHub: ",
                    html.A(REPOSITORY_URL, href=REPOSITORY_URL, target="_blank"), "."]),
            html.P(["For comments and suggestions for improvement, contact ", _ext(CONTACT_NAME, CONTACT_URL), " (",
                    html.A(CONTACT_EMAIL, href=f"mailto:{CONTACT_EMAIL}"), ")."]),
        ], title="Data, code and contact"),
    ])
