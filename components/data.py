"""Data access layer.

Reads data/smart_buildings_dataset.xlsx. The workbook is re-read automatically when
the file changes on disk, so editing the Excel file and refreshing the browser is
enough to see new data (no restart needed).

The sheet 'data_dictionary' drives the app: label, unit, group, dtype and description of every column.
All columns are offered in the dropdowns that fit their dtype (numeric / categorical); the 'hover' flag (Y)
marks the parameters always shown in hover pop-ups.
"""
from __future__ import annotations

import math
from typing import Any
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from dash import html

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "smart_buildings_dataset.xlsx"

SBP_LEVEL_NAMES = {
    -2: "No technological equipment",
    -1: "Pre-automated",
    0: "Automated",
    1: "Smart ready",
    2: "Smart standard",
    3: "Smart predictive",
    4: "Smart cognitive",
}


@dataclass
class Dataset:
    buildings: pd.DataFrame
    detailed: pd.DataFrame
    dictionary: pd.DataFrame
    sources: pd.DataFrame
    mtime: float


_cache: Dataset | None = None


def get_data() -> Dataset:
    """Return the dataset, reloading it if the Excel file was modified."""
    global _cache
    mtime = DATA_FILE.stat().st_mtime
    if _cache is None or _cache.mtime != mtime:
        sheets = pd.read_excel(DATA_FILE, sheet_name=None)
        b = sheets["buildings"]
        b = b[b["building_id"].notna()].copy()
        b["building_id"] = b["building_id"].astype(str)
        if "short_name" not in b.columns:
            b["short_name"] = b["building_id"]
        b["short_name"] = b["short_name"].fillna(b["building_id"]).astype(str)
        d = sheets.get("data_dictionary", pd.DataFrame(columns=["column", "label", "unit", "group", "dtype"]))
        d = d[d["column"].isin(b.columns)].fillna("")
        _cache = Dataset(
            buildings=b.reset_index(drop=True),
            detailed=sheets.get("sri_detailed", pd.DataFrame(columns=["building_id", "domain", "impact", "score_pct"])),
            dictionary=d.reset_index(drop=True),
            sources=sheets.get("sources", pd.DataFrame()),
            mtime=mtime,
        )
    return _cache


# ----------------------------------------------------------------- dictionary helpers
def _meta(col: str) -> dict:
    d = get_data().dictionary
    row = d[d["column"] == col]
    return row.iloc[0].to_dict() if len(row) else {"column": col, "label": col, "unit": "", "group": "", "dtype": ""}


def label(col: str, with_unit: bool = True) -> str:
    m = _meta(col)
    lab = m.get("label") or col
    unit = m.get("unit") or ""
    return f"{lab} [{unit}]" if with_unit and unit else lab


def unit(col: str) -> str:
    return _meta(col).get("unit") or ""


def description(col: str) -> str:
    """Description of a column from the data dictionary ('' if none)."""
    return str(_meta(col).get("description") or "").strip()


def tooltip(col: str) -> str:
    """Hover text for a parameter: label, unit, description and data coverage."""
    lines = [label(col)]
    desc = description(col)
    if desc:
        lines.append(desc)
    b = get_data().buildings
    if col in b.columns:
        lines.append(f"Values available for {int(b[col].notna().sum())} of {len(b)} buildings.")
    return "\n".join(lines)


def is_numeric(col: str) -> bool:
    """True for numeric parameters. Uses the data-dictionary dtype when given (so an empty column declared
    'numeric' or 'categorical' is treated correctly), otherwise the pandas dtype of the column."""
    b = get_data().buildings
    if col not in b.columns:
        return False
    dtype = str(_meta(col).get("dtype") or "").strip().lower()
    if dtype == "numeric":
        return True
    if dtype in ("categorical", "text"):
        return False
    return pd.api.types.is_numeric_dtype(b[col])


def has_data(col: str) -> bool:
    b = get_data().buildings
    return col in b.columns and bool(b[col].notna().any())


def all_columns() -> list[str]:
    """All columns of the 'buildings' sheet: data-dictionary order first, then any undocumented columns."""
    data = get_data()
    cols = [c for c in data.dictionary["column"] if c in data.buildings.columns]
    return cols + [c for c in data.buildings.columns if c not in cols]


def columns_for(use: str, kind: str | None = None, include_empty: bool = False) -> list[str]:
    """Parameters offered for a given use.

    Every column of the dataset is offered, according to its type:
      - kind='numeric'      -> numeric parameters (bubble size, X/Y axes, numeric filters, statistics)
      - kind='categorical'  -> text / categorical parameters (category filters)
      - kind=None           -> all parameters (bubble colour, colour by)
    use='hover' is the exception: only columns flagged 'Y' in the 'hover' column of the data dictionary
    are always shown in the map / plot hover pop-ups.
    Columns without any value are skipped unless include_empty=True (dropdowns then show them disabled).
    """
    if use == "hover":
        d = get_data().dictionary
        if "hover" not in d.columns:
            return []
        cols = d.loc[d["hover"].astype(str).str.upper().str.strip() == "Y", "column"].tolist()
    else:
        cols = all_columns()
    out = []
    for c in cols:
        if not include_empty and not has_data(c):
            continue
        num = is_numeric(c)
        if (kind == "numeric" and not num) or (kind == "categorical" and num):
            continue
        out.append(c)
    return out


def hover_label(text: str, title: str) -> html.Span:
    """Option label with a hover description (browser tooltip). Used in dropdown menus: the tooltip
    shows when hovering an option in the open list and when hovering the selected value."""
    return html.Span(text, title=title, className="opt-label")


def dropdown_options(cols: list[str]) -> list[Any]:
    """Dropdown options shown as 'Group · Label', with the parameter description on hover.

    Labels are components (for the hover text), so 'search' holds the searchable text:
    group, label and column name.
    """
    opts = []
    for c in cols:
        m = _meta(c)
        grp = m.get("group") or ""
        text = f"{grp} · {label(c)}" if grp else label(c)
        empty = not has_data(c)
        if empty:
            text += " (no data yet)"
        opts.append({"label": hover_label(text, tooltip(c)), "value": c, "search": f"{text} {c}",
                     "disabled": empty})  # empty parameters are listed but cannot be selected
    return opts


def fmt(col: str, value) -> str:
    """Human-readable value with unit."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    u = unit(col)
    if isinstance(value, (int, float)):
        if u == "%":
            return f"{value:.1f} %"
        if u.startswith("level"):
            return f"{value:.2f}"
        if u == "m²":
            return f"{value:,.0f} m²".replace(",", " ")
        if u == "°":
            return f"{value:.5f}°"
        if float(value).is_integer():
            return f"{int(value)}"
        return f"{value:.2f}"
    return str(value)


def sbp_level_name(level) -> str:
    if level is None or (isinstance(level, float) and math.isnan(level)):
        return "n/a"
    return SBP_LEVEL_NAMES.get(int(math.floor(level)), "")


def building_options() -> list[Any]:
    b = get_data().buildings
    def title(r):
        parts = [str(x) for x in (getattr(r, "building_type", None), getattr(r, "city", None),
                                  getattr(r, "construction_period", None)) if isinstance(x, str) and x]
        return " · ".join(parts)
    opts = []
    for r in b.itertuples():
        text = f"{r.short_name} — {r.building_name}"
        opts.append({"label": hover_label(text, title(r) or text), "value": r.building_id, "search": text})
    return opts


def get_building(building_id: str) -> pd.Series | None:
    b = get_data().buildings
    row = b[b["building_id"] == building_id]
    return row.iloc[0] if len(row) else None
