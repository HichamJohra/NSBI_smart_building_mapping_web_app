# NSBI_smart_building_mapping_web_app
Web app to map and explore smart buildings around the world [NSBI project]

Multi-page [Dash](https://dash.plotly.com/) web app to map and explore smart building cases
(Smart Readiness Indicator and Smart by Powerhouse assessments) from an embedded Excel dataset.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python app.py                 # -> http://127.0.0.1:8050
```

## Project structure

| Path | Purpose |
|---|---|
| `app.py` | App entry point, navigation bar, page container |
| `pages/home.py` | Dashboard: KPIs, add/remove filters, bubble map, statistics cards, XY correlation explorer, full dataset table |
| `pages/building.py` | Building detail: characteristics, building performance indicators, location map, SRI key functionalities, impacts, domains, detailed matrix, SbP topics |
| `pages/compare.py` | Compare 2–6 buildings on radar and bar charts |
| `pages/about.py` | Frameworks (SRI, Smart by Powerhouse), scales, sources, caveats |
| `components/data.py` | Excel loading (auto-reload on file change) and data-dictionary helpers |
| `components/figures.py` | Plotly figure builders |
| `assets/style.css` | Styling (auto-loaded by Dash) |
| `assets/favicon.ico`, `assets/logos/` | SINTEF browser-tab icon; SINTEF and IBPSA Nordic logos (top right of every page, linked to their websites); NSBI logo (About page) |
| `data/smart_buildings_dataset.xlsx` | The dataset |
| `docs/` | Documentation: architecture, data model, development guide |
| `docs/project_graph_explorer/` | Interactive HTML map of the code + script to regenerate it |

## Documentation

See [docs/README.md](docs/README.md). For an interactive overview of files, imports, function calls and
callback inputs/outputs, open `docs/project_graph_explorer/NSBI_project_explorer.html` in a browser.
Regenerate it after code changes:

```bash
.venv\Scripts\python.exe docs/project_graph_explorer/build_project_explorer.py
```

## Dataset

`data/smart_buildings_dataset.xlsx` contains:

- `buildings` – one row per building (identity, location, characteristics, SRI and SbP results)
- `sri_detailed` – SRI score per technical domain × impact criterion (long format)
- `data_dictionary` – label, unit, group, dtype and description of each column. Every column appears in the
  dropdowns that fit its dtype (numeric or category); `hover` = `Y` shows it in all hover pop-ups
- `sources` – references

To add a parameter, add a column to `buildings` and a row to `data_dictionary`. To add a building, add a row
to `buildings`. Refresh the browser: the file is re-read automatically when it changes.

Current content: 7 EDISON pilot buildings (SINTEF Notes, EDISON D1.1a, 2026) and 10 municipal buildings in
Ålesund (Campodonico Avendaño et al., 2024, *Energy and Buildings* 314, 114234).
