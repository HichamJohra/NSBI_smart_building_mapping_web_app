# Development

## Requirements

- [uv](https://docs.astral.sh/uv/) (installs Python and all dependencies), e.g. on Windows:
  `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- Git
- An IDE; the project is developed with PyCharm (2026)

Supported Python versions: 3.11 to 3.14 (tested in CI). The app runs on Python 3.13 locally (`.python-version`) and
in the Docker image.

## Setup

In a terminal, in the project folder:

```
uv sync                         # creates .venv with the app, dev tools (pytest, Ruff, mypy, pre-commit) and tools/ extras
uv run pre-commit install       # run the checks automatically before each commit
```

`pyproject.toml` lists the dependencies; `uv.lock` pins their exact versions (commit both). `uv add PACKAGE` adds a
dependency, `uv lock --upgrade` upgrades them all (then run the tests).

PyCharm: **Settings → Python → Interpreter → Add Interpreter → Add Local Interpreter → uv** (or select the existing
`.venv\Scripts\python.exe`). PyCharm runs pytest from the test files directly.

## Run

- `uv run python app.py`, or right-click `app.py` → **Run 'app'**, then open <http://127.0.0.1:8050>.
- `debug=True`: saving a `.py` file reloads the server; refresh the browser.
- Editing the Excel file needs no restart: the dataset is re-read when the file changes.
- Breakpoints: **Debug 'app'**. If they are not hit, use `app.run(debug=True, use_reloader=False)` temporarily.

## Tests and code checks

```
uv run pytest                   # all tests (tests/), add --cov for coverage
uv run pre-commit run -a        # every check: whitespace, YAML/TOML, Ruff lint + format, uv.lock, mypy
```

| Test file | Checks |
|---|---|
| `tests/test_dataset.py` | The Excel dataset: unique IDs, required fields, coordinates, data dictionary, numeric columns, SRI ranges and classes, years, climate zones, validation statuses, sources |
| `tests/test_submissions.py` | Data contributions: validation rules, template, upload, storage (temporary folder), anti-spam and rate limit |
| `tests/test_app.py` | The Dash app: pages registered and served, layouts, filters, table, KPIs, map and correlation figures, every building page, compare page |

Run the tests after every change of the dataset: they catch typos such as a duplicate `building_id`, a text in a
numeric column or an unknown climate zone before the change reaches the deployed app.

Ruff settings, the mypy configuration (not yet `strict`) and the pytest options are in `pyproject.toml`; the
pre-commit hooks are in `.pre-commit-config.yaml`.

## Continuous integration (GitHub Actions)

`.github/workflows/ci.yml` runs on every push to `dev` or `main`, on every pull request and on demand (**Actions →
CI → Run workflow**):

- **checks**: `pre-commit run --all-files` (same checks as locally);
- **tests**: `pytest --cov` on Python 3.11, 3.12, 3.13 and 3.14 (Ubuntu) and Python 3.13 (Windows).

Results appear next to each commit and on the pull request. To block merging into `main` when a job fails, add the
CI jobs as **required status checks** in the `main` ruleset (GitHub → Settings → Rules → Rulesets → main → *Require
status checks to pass*).

## Git workflow

`main` is protected on GitHub (ruleset: pull request required, no force push, no deletion). Work on `dev`:

```
git switch dev                # work branch
git pull                      # before starting
git status                    # check: no .venv, .idea, __pycache__
git add .
git commit -m "Short description"   # pre-commit runs the checks; fix or re-add the files it changed
git push                      # -> origin/dev, CI runs
```

When `dev` is stable and CI is green: on GitHub, open a pull request `dev` → `main` and merge it (this deploys the
app, see [deployment.md](deployment.md)). Then update the local `main` with `git switch main`, `git pull`,
`git switch dev`.

Line endings are fixed to LF by `.gitattributes` (binary files such as `.xlsx` and `.png` are never converted).

Working documents (reports, drafts, raw material) are kept **outside** the repository.

## After changing the code

Regenerate the project graph explorer so the documentation stays in sync:

```
uv run python docs/project_graph_explorer/build_project_explorer.py
```

## Deployment

`app.server` is the WSGI entry point (`gunicorn app:server` in the Docker image). See [deployment.md](deployment.md).
