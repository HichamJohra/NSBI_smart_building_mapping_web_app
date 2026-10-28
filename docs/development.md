# Development

## Requirements

- Python 3.12 or 3.13
- Git
- An IDE; the project is developed with PyCharm (2026)

## Setup (PyCharm)

1. **File → Open…** → select the project folder.
2. Interpreter: click the interpreter widget (bottom-right) → **Add New Interpreter → Add Local Interpreter →
   Virtualenv**, location `.venv` in the project folder.
3. Install the dependencies in the PyCharm Terminal:
   ```
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
   (Calling the venv's `python.exe` directly avoids PowerShell's script-execution policy for `Activate.ps1`.)

## Run

- Right-click `app.py` → **Run 'app'**, then open <http://127.0.0.1:8050>.
- `debug=True`: saving a `.py` file reloads the server; refresh the browser.
- Editing the Excel file needs no restart: the dataset is re-read when the file changes.
- Breakpoints: **Debug 'app'**. If they are not hit, use `app.run(debug=True, use_reloader=False)` temporarily.

## Git workflow

```
git pull                      # before starting
git status                    # check: no .venv, .idea, __pycache__
git add .
git commit -m "Short description"
git push
```

Working documents (reports, drafts, raw material) are kept **outside** the repository.

## After changing the code

Regenerate the project graph explorer so the documentation stays in sync:

```
.venv\Scripts\python.exe docs/project_graph_explorer/build_project_explorer.py
```

## Deployment (later)

`app.server` is the WSGI entry point, e.g. `gunicorn app:server` on Linux hosting.
