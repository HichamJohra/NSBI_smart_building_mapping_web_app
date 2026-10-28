# Project graph explorer

`NSBI_project_explorer.html` is an interactive, self-contained (offline) map of the code. Open it in a web
browser.

| View | Shows |
|---|---|
| Folder & file structure | Folders → files → top-level functions |
| Module imports | Which file imports from which; Dash conventions (pages, assets); data file readers |
| Function calls | Which function calls which (optionally external libraries and the Dash runtime) |
| Callback data flow | Component property (Input / State) → callback → component property (Output) |

Click a node to trace its dependencies (orange = upstream, blue = downstream); the right panel shows
signatures, docstrings, callback inputs/outputs, callers and callees.

## Regenerate

Run from the project root after code changes (static analysis only; the app is not executed):

```
.venv\Scripts\python.exe docs/project_graph_explorer/build_project_explorer.py
```

Optional arguments:

| Argument | Default | Purpose |
|---|---|---|
| `--root DIR` | two folders above the script | Project root |
| `--out FILE` | `NSBI_project_explorer.html` here | Output file |
| `--include-docs` | off | Pre-tick the "Include docs/ tooling code" checkbox in the generated page |

## Files

| File | Purpose |
|---|---|
| `build_project_explorer.py` | Analyses the code with Python's `ast` module and writes the HTML |
| `explorer_template.html` | Page template (HTML/CSS/JS, no external libraries); the data is injected at `/*__DATA__*/null` |
| `NSBI_project_explorer.html` | Generated output |

Python code under `docs/` (documentation tooling such as `build_project_explorer.py`) is analysed but hidden
by default, because it is not part of the app. Tick **Include docs/ tooling code** in the explorer (structure,
imports and function-call views) to show it, or generate the page with `--include-docs` to have it shown by default.
