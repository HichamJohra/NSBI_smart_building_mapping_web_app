# NSBI_smart_building_mapping_web_app
Web app to map and explore smart buildings around the world [NSBI project]

Multi-page [Dash](https://dash.plotly.com/) web app to map and explore smart building cases
(Smart Readiness Indicator and Smart by Powerhouse assessments) from an embedded Excel dataset.

[![CI](https://github.com/HichamJohra/NSBI_smart_building_mapping_web_app/actions/workflows/ci.yml/badge.svg)](https://github.com/HichamJohra/NSBI_smart_building_mapping_web_app/actions/workflows/ci.yml)

## Run locally

With [uv](https://docs.astral.sh/uv/) (Python 3.11–3.14):

```bash
uv sync                       # create .venv with the exact versions of uv.lock
uv run python app.py          # -> http://127.0.0.1:8050
uv run pytest                 # tests
uv run pre-commit run -a      # code checks (Ruff, mypy, ...)
```

See [docs/development.md](docs/development.md) for the full setup, the tests and the CI workflow.

## Project structure

| Path | Purpose |
|---|---|
| `app.py` | App entry point, navigation bar, page container |
| `pages/home.py` | Dashboard: KPIs, add/remove filters, bubble map, statistics cards, XY correlation explorer, full dataset table |
| `pages/building.py` | Building detail: characteristics, building performance indicators, location map, SRI key functionalities, impacts, domains, detailed matrix, SbP topics |
| `pages/compare.py` | Compare 2–6 buildings on radar and bar charts |
| `pages/contribute.py` | Contribute data: online form or Excel template upload, validated and stored for review |
| `pages/about.py` | Frameworks (SRI, Smart by Powerhouse), scales, sources, caveats |
| `components/data.py` | Excel loading (auto-reload on file change) and data-dictionary helpers |
| `components/figures.py` | Plotly figure builders |
| `components/submissions.py` | Data contributions: template, validation, anti-spam checks, storage |
| `tools/fetch_submissions.py` | Maintainer script: download (and delete) the contributions from the server |
| `tests/` | pytest suite: dataset integrity, data contributions, app pages and callbacks |
| `pyproject.toml`, `uv.lock`, `.python-version` | Dependencies (exact versions in `uv.lock`) and settings of Ruff, mypy, pytest |
| `.pre-commit-config.yaml`, `.github/workflows/ci.yml` | Code checks before each commit; CI on GitHub (checks + tests on Python 3.11–3.14 and Windows) |
| `Dockerfile`, `.dockerignore` | Container image for Docker / Google Cloud Run, built with uv (see `docs/deployment.md`) |
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
Ålesund (Campodonico Avendaño et al., 2024, *Energy and Buildings* 314, 114234), and 3 pilot buildings of the
H2020 ARV project (Oslo, Trento, Karviná; ARV D8.4, 2026), 1 European Commission SRI case study (NeoBuild,
Luxembourg), 36 buildings of the H2020 TIMEPAC project (D2.4, 2023; Austria, Croatia, Cyprus, Italy, Slovenia,
Spain), 9 pilots of the Horizon Europe SmartLivingEPC project (D2.4; Greece, Cyprus, Estonia, Spain), and 92
buildings (42 non-residential, 50 residential) from the SRI datasets of Caracci et al. (2026, *Energy & Buildings*
358, 117215 and *Energies* 19, 4762), each referenced to its original study. 158 buildings in total.
