"""Data contributions: template, validation, anti-bot checks and storage of submitted buildings.

Submissions are written as Excel files into SUBMISSIONS_DIR:
  - locally: ./submissions (git-ignored)
  - on Google Cloud Run: a private Cloud Storage bucket mounted as a folder (see docs/deployment.md)
They are collected (downloaded + deleted) with tools/fetch_submissions.py. Submissions never modify the
published dataset: the maintainer reviews them and copies accepted rows into data/smart_buildings_dataset.xlsx.

No personal data is collected (no name, no e-mail). The client IP address is only held in memory for a few
minutes for rate limiting and is never written to disk.

Settings (environment variables):
  SUBMISSIONS_DIR       folder where submissions are written           (default: <project>/submissions)
  MAX_UPLOAD_MB         maximum size of an uploaded Excel file in MB   (default: 5)
  SUBMISSION_SECRET     secret key signing the anti-spam check; set it in production so that all
                        server instances share it                       (default: random per process)
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import io
import math
import os
import random
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import Workbook
from openpyxl.xml import DEFUSEDXML  # True when defusedxml is installed: openpyxl then parses XML safely
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from components.data import all_columns, description, get_data, is_numeric, label, unit

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SUBMISSIONS_DIR = Path(os.environ.get("SUBMISSIONS_DIR", PROJECT_ROOT / "submissions"))
MAX_UPLOAD_MB = float(os.environ.get("MAX_UPLOAD_MB", "5"))
MAX_UPLOAD_BYTES = int(MAX_UPLOAD_MB * 1024 * 1024)
MAX_ROWS_PER_UPLOAD = 500
MAX_TEXT_LENGTH = 2000

# Columns that contributors must fill in (form and every row of an uploaded file)
REQUIRED = ["building_name", "city", "country", "latitude", "longitude", "building_type",
            "construction_period", "main_reference"]
# Groups of which at least one value must be given (a building without any result is not useful)
RESULT_GROUPS = ["SRI", "SRI key functionality", "SRI impact criteria", "SRI technical domains",
                 "Smart by Powerhouse", "Smart by Powerhouse topics", "Building performance"]
# Columns not offered to contributors (assigned by the maintainer)
NOT_CONTRIBUTED = {"building_id"}

# Anti-spam settings
MIN_SECONDS_ON_PAGE = 5          # faster than this = bot
TOKEN_MAX_AGE_S = 6 * 3600       # the page must be reloaded after 6 h
RATE_LIMITS = [(600, 5), (86400, 30)]  # (window in seconds, max submissions) per client IP and server instance

_SECRET = os.environ.get("SUBMISSION_SECRET", "").encode() or secrets.token_bytes(32)

if not DEFUSEDXML:  # uploads are still size-limited, but XML-bomb protection is missing
    print("WARNING: 'defusedxml' is not installed; run pip install -r requirements.txt", flush=True)


# ----------------------------------------------------------------- columns and rules
def contributed_columns() -> list[str]:
    return [c for c in all_columns() if c not in NOT_CONTRIBUTED]


def _year_now() -> int:
    return dt.date.today().year


def value_range(col: str) -> tuple[float, float] | None:
    """Plausible numeric range of a parameter (None = no check)."""
    u = unit(col)
    if col == "latitude":
        return -90, 90
    if col == "longitude":
        return -180, 180
    if col.endswith("_year") or col == "reference_year":
        return 1800, _year_now() + 5
    if u.startswith("level"):
        return -2, 4
    if u == "%":
        return -100, 100  # SRI domain scores can be negative
    if col.startswith(("operational_carbon", "grid_", "carbon_intensity", "whole_life", "embodied")):
        return None  # can be negative (e.g. net export, carbon credits)
    if is_numeric(col):
        return 0, math.inf
    return None


def _to_number(v: Any) -> float | None:
    """Number from a form / Excel value; accepts '12,5'. Raises ValueError when not a number."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    if isinstance(v, bool):
        raise ValueError
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("−", "-").replace(" ", "")
    if not s:
        return None
    return float(s.replace(",", "."))


def _is_empty(v: Any) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v)) or (isinstance(v, str) and not v.strip())


def clean_record(raw: dict) -> tuple[dict, list[str]]:
    """Type-check and normalise one building. Returns (clean record, list of error messages)."""
    errors: list[str] = []
    rec: dict[str, Any] = {}
    groups = dict(zip(get_data().dictionary["column"], get_data().dictionary["group"]))
    for col in contributed_columns():
        v = raw.get(col)
        if _is_empty(v):
            rec[col] = None
            continue
        if is_numeric(col):
            try:
                num = _to_number(v)
            except (TypeError, ValueError):
                errors.append(f"{label(col)}: '{v}' is not a number.")
                continue
            rng = value_range(col)
            if num is not None and rng and not (rng[0] <= num <= rng[1]):
                hi = "∞" if math.isinf(rng[1]) else f"{rng[1]:g}"
                errors.append(f"{label(col)}: {num:g} is outside the plausible range {rng[0]:g} … {hi}.")
            if num is not None and (col.endswith("_year") or col == "reference_year") and not float(num).is_integer():
                errors.append(f"{label(col)}: a year must be a whole number.")
            rec[col] = num
        else:
            s = str(v).strip()
            if len(s) > MAX_TEXT_LENGTH:
                errors.append(f"{label(col)}: text is too long (max {MAX_TEXT_LENGTH} characters).")
            rec[col] = s[:MAX_TEXT_LENGTH]
    for col in REQUIRED:
        if col in rec and rec[col] is None:
            errors.append(f"{label(col, with_unit=False)} is required.")
    if not any(rec.get(c) is not None for c, g in groups.items() if g in RESULT_GROUPS and c in rec):
        errors.append("Give at least one result: an SRI score, a Smart by Powerhouse level or a building "
                      "performance indicator.")
    return rec, errors


def parse_upload(contents: str, filename: str) -> tuple[list[dict], list[str]]:
    """Decode and validate an uploaded Excel file (dcc.Upload 'contents'). Returns (records, errors)."""
    if not filename or not filename.lower().endswith(".xlsx"):
        return [], ["Please upload an Excel file (.xlsx), preferably the template from this page."]
    try:
        data = base64.b64decode(contents.split(",", 1)[1])
    except (IndexError, ValueError):
        return [], ["The file could not be read."]
    if len(data) > MAX_UPLOAD_BYTES:
        return [], [f"The file is too large ({len(data) / 1e6:.1f} MB). The maximum is {MAX_UPLOAD_MB:g} MB."]
    try:
        sheets = pd.read_excel(io.BytesIO(data), sheet_name=None, dtype=object, engine="openpyxl")
    except Exception:  # corrupt / not an Excel file
        return [], ["The file is not a valid Excel workbook."]
    df = sheets.get("buildings", next(iter(sheets.values())) if sheets else None)
    if df is None or df.empty:
        return [], ["The 'buildings' sheet is empty."]
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all")
    known = set(contributed_columns())
    unknown = [c for c in df.columns if c not in known and not c.startswith("Unnamed")]
    if unknown:
        return [], ["Unknown column(s): " + ", ".join(unknown[:10]) + (" …" if len(unknown) > 10 else "")
                    + ". Use the column names of the template (first row)."]
    if len(df) > MAX_ROWS_PER_UPLOAD:
        return [], [f"Too many rows ({len(df)}). The maximum is {MAX_ROWS_PER_UPLOAD} buildings per file."]
    records, errors = [], []
    for i, (_, row) in enumerate(df.iterrows(), start=2):  # Excel row numbers (row 1 = header)
        rec, errs = clean_record({c: row[c] for c in df.columns if c in known})
        records.append(rec)
        errors += [f"Row {i}: {e}" for e in errs]
    return records, errors


# ----------------------------------------------------------------- Excel files
def _header_style(ws) -> None:
    fill = PatternFill("solid", fgColor="1F4E79")
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = fill
        c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"


def _set(ws, row: int, col: int, value: Any) -> None:
    """Write a cell; text is always stored as text (never as a formula: protects against formula injection)."""
    cell = ws.cell(row=row, column=col, value=value)
    if isinstance(value, str):
        cell.data_type = "s"


def template_bytes() -> bytes:
    """Empty Excel template: 'buildings' (column names) + 'data_dictionary' + 'instructions'."""
    cols = contributed_columns()
    wb = Workbook()
    ws = wb.active
    ws.title = "buildings"
    for j, c in enumerate(cols, start=1):
        _set(ws, 1, j, c)
        ws.column_dimensions[get_column_letter(j)].width = max(14, min(40, len(c) + 2))
    _header_style(ws)

    dd = wb.create_sheet("data_dictionary")
    head = ["column", "label", "unit", "type", "required", "plausible range", "description"]
    for j, h in enumerate(head, start=1):
        _set(dd, 1, j, h)
    for i, c in enumerate(cols, start=2):
        rng = value_range(c)
        rng_txt = "" if not rng else f"{rng[0]:g} … {'∞' if math.isinf(rng[1]) else f'{rng[1]:g}'}"
        vals = [c, label(c, with_unit=False), unit(c), "number" if is_numeric(c) else "text",
                "yes" if c in REQUIRED else "", rng_txt, description(c)]
        for j, v in enumerate(vals, start=1):
            _set(dd, i, j, v)
    for j, w in enumerate([34, 40, 16, 9, 9, 16, 100], start=1):
        dd.column_dimensions[get_column_letter(j)].width = w
    _header_style(dd)

    ins = wb.create_sheet("instructions")
    lines = [
        "NSBI Smart Building Mapping – data contribution template",
        "",
        "1. Fill in one row per building in the sheet 'buildings'. Do not rename or reorder the columns of row 1.",
        f"2. Required columns: {', '.join(REQUIRED)}, and at least one result (SRI, Smart by Powerhouse or "
        "building performance).",
        "3. See the sheet 'data_dictionary' for the meaning, unit, type and plausible range of every column.",
        "4. Numbers only in numeric columns (percentages as 0–100, e.g. 62.6). Leave a cell empty when unknown.",
        "5. Do not include personal data (names, e-mail addresses, phone numbers).",
        f"6. Upload the file on the 'Contribute data' page of the web app (max {MAX_UPLOAD_MB:g} MB, "
        f"max {MAX_ROWS_PER_UPLOAD} buildings).",
    ]
    for i, t in enumerate(lines, start=1):
        _set(ins, i, 1, t)
    ins["A1"].font = Font(bold=True, size=13)
    ins.column_dimensions["A"].width = 120
    wb.move_sheet("instructions", offset=-2)
    wb.active = 0
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _slug(text: str, n: int = 30) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", str(text or "")).strip("-")
    return s[:n] or "building"


def save_submission(records: list[dict], kind: str, comment: str = "", original_filename: str = "") -> str:
    """Write the submitted buildings to a new Excel file in SUBMISSIONS_DIR. Returns the submission id."""
    now = dt.datetime.now(dt.timezone.utc)
    sub_id = f"{now:%Y%m%d-%H%M%S}-{secrets.token_hex(3)}"
    first = records[0].get("building_name") if records else ""
    name = f"{sub_id}_{kind}_{_slug(first)}{'_and-more' if len(records) > 1 else ''}.xlsx"
    cols = contributed_columns()

    wb = Workbook()
    ws = wb.active
    ws.title = "buildings"
    for j, c in enumerate(cols, start=1):
        _set(ws, 1, j, c)
    for i, rec in enumerate(records, start=2):
        for j, c in enumerate(cols, start=1):
            _set(ws, i, j, rec.get(c))
    _header_style(ws)
    info = wb.create_sheet("submission_info")
    rows = [("submission_id", sub_id), ("received_utc", now.strftime("%Y-%m-%d %H:%M:%S")),
            ("channel", kind), ("buildings", len(records)), ("original_filename", original_filename or ""),
            ("comment", (comment or "")[:MAX_TEXT_LENGTH])]
    for i, (k, v) in enumerate(rows, start=1):
        _set(info, i, 1, k)
        _set(info, i, 2, v)
    info.column_dimensions["A"].width = 20
    info.column_dimensions["B"].width = 80

    buf = io.BytesIO()
    wb.save(buf)
    SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
    # One sequential write of the complete file. On a mounted Cloud Storage bucket the object is created
    # when the file is closed, so a partially written submission is never visible.
    with open(SUBMISSIONS_DIR / name, "wb") as f:
        f.write(buf.getvalue())
    return sub_id


# ----------------------------------------------------------------- anti-spam
def new_challenge() -> tuple[str, dict]:
    """A small sum to solve + a signed token (page-load time and answer). No server-side state needed."""
    a, b = random.randint(2, 9), random.randint(2, 9)
    ts = int(time.time())
    sig = hmac.new(_SECRET, f"{ts}:{a + b}".encode(), hashlib.sha256).hexdigest()
    return f"What is {a} + {b}?", {"ts": ts, "sig": sig}


def check_human(token: dict | None, answer: Any, honeypot: str | None) -> str | None:
    """None if the request looks human, else the reason (shown to the user, except for the honeypot)."""
    if honeypot:
        return "bot"  # hidden field filled in: silently ignored by the caller
    if not token or "ts" not in token or "sig" not in token:
        return "The page has expired. Please reload it."
    age = time.time() - float(token["ts"])
    if age > TOKEN_MAX_AGE_S:
        return "The page has expired. Please reload it."
    if age < MIN_SECONDS_ON_PAGE:
        return "Please take a moment to check your entry before sending."
    try:
        ans = int(_to_number(answer))
    except (TypeError, ValueError):
        return "Please answer the anti-spam question."
    expected = hmac.new(_SECRET, f"{int(token['ts'])}:{ans}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, str(token["sig"])):
        return "The answer to the anti-spam question is not correct."
    return None


_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def rate_limited(client: str) -> bool:
    """True if this client sent too many submissions recently (kept in memory only, per server instance)."""
    now = time.time()
    longest = max(w for w, _ in RATE_LIMITS)
    with _lock:
        q = _hits[client]
        while q and now - q[0] > longest:
            q.popleft()
        if any(sum(1 for t in q if now - t <= w) >= n for w, n in RATE_LIMITS):
            return True
        q.append(now)
        return False


def client_id() -> str:
    """Client IP for rate limiting (behind Cloud Run's proxy the first X-Forwarded-For entry is the client)."""
    try:
        from flask import request
        fwd = request.headers.get("X-Forwarded-For", "")
        return fwd.split(",")[0].strip() or (request.remote_addr or "unknown")
    except (RuntimeError, ImportError):  # outside a request (tests)
        return "local"
