"""Data contributions: validation, Excel template and upload, storage and anti-spam checks."""

from __future__ import annotations

import base64
import io
import time
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from openpyxl import Workbook, load_workbook

from components import submissions as sub

XLSX_MIME = "data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,"


def valid_record(**changes: Any) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "building_name": "Test school",
        "city": "Oslo",
        "country": "Norway",
        "latitude": 59.91,
        "longitude": 10.75,
        "building_type": "School",
        "construction_period": "After 2010",
        "main_reference": "Test report (2026)",
        "sri_total_pct": 42.5,
    }
    rec.update(changes)
    return rec


def upload(rows: list[dict[str, Any]], columns: list[str] | None = None) -> str:
    """A dcc.Upload 'contents' string for an Excel file with the given rows."""
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "buildings"
    cols = columns or list(rows[0])
    ws.append(cols)
    for r in rows:
        ws.append([r.get(c) for c in cols])
    buf = io.BytesIO()
    wb.save(buf)
    return XLSX_MIME + base64.b64encode(buf.getvalue()).decode()


# ------------------------------------------------------------------ rules
def test_value_ranges() -> None:
    assert sub.value_range("latitude") == (-90, 90)
    assert sub.value_range("longitude") == (-180, 180)
    assert sub.value_range("sri_total_pct") == (-100, 100)
    assert sub.value_range("sbp_level") == (-2, 4)
    assert sub.value_range("building_name") is None


def test_maintainer_columns_not_contributed() -> None:
    cols = sub.contributed_columns()
    assert "building_id" not in cols
    assert "validation_status" not in cols
    assert set(sub.REQUIRED) <= set(cols)


@pytest.mark.parametrize(
    ("raw", "expected"), [("12,5", 12.5), (" −3 ", -3.0), ("1 000", 1000.0), (7, 7.0), ("", None), (None, None)]
)
def test_to_number(raw: Any, expected: float | None) -> None:
    assert sub._to_number(raw) == expected


@pytest.mark.parametrize("raw", ["abc", True])
def test_to_number_rejects(raw: Any) -> None:
    with pytest.raises(ValueError):  # noqa: PT011
        sub._to_number(raw)


# ------------------------------------------------------------------ clean_record
def test_valid_record_accepted() -> None:
    rec, errors = sub.clean_record(valid_record())
    assert errors == []
    assert rec["sri_total_pct"] == 42.5
    assert rec["building_name"] == "Test school"


def test_climate_zone_code_is_normalised() -> None:
    rec, errors = sub.clean_record(valid_record(ashrae_climate_zone="6a"))
    assert errors == []
    assert rec["ashrae_climate_zone"] == "6A (Cold – Humid)"


def test_unknown_climate_zone_refused() -> None:
    _, errors = sub.clean_record(valid_record(ashrae_climate_zone="9Z"))
    assert any("not a valid value" in e for e in errors)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"city": None}, "is required"),
        ({"latitude": 123}, "outside the plausible range"),
        ({"longitude": "east"}, "is not a number"),
        ({"construction_year": 1999.5}, "whole number"),
        ({"sri_total_pct": None}, "at least one result"),
    ],
)
def test_invalid_records_refused(changes: dict[str, Any], message: str) -> None:
    _, errors = sub.clean_record(valid_record(**changes))
    assert any(message in e for e in errors), errors


def test_long_text_refused() -> None:
    _, errors = sub.clean_record(valid_record(notes="x" * (sub.MAX_TEXT_LENGTH + 1)))
    assert any("too long" in e for e in errors)


# ------------------------------------------------------------------ Excel template and upload
def test_template_has_contributed_columns() -> None:
    wb = load_workbook(io.BytesIO(sub.template_bytes()))
    assert {"buildings", "data_dictionary", "instructions"} <= set(wb.sheetnames)
    header = [c.value for c in wb["buildings"][1]]
    assert header == sub.contributed_columns()


def test_upload_round_trip() -> None:
    records, errors = sub.parse_upload(upload([valid_record(), valid_record(building_name="Second")]), "a.xlsx")
    assert errors == []
    assert [r["building_name"] for r in records] == ["Test school", "Second"]


def test_upload_reports_row_numbers() -> None:
    _, errors = sub.parse_upload(upload([valid_record(), valid_record(latitude=200)]), "a.xlsx")
    assert errors
    assert errors[0].startswith("Row 3:")


def test_upload_wrong_extension() -> None:
    _, errors = sub.parse_upload(upload([valid_record()]), "a.csv")
    assert "Excel file" in errors[0]


def test_upload_unknown_column() -> None:
    _, errors = sub.parse_upload(upload([{**valid_record(), "password": "x"}]), "a.xlsx")
    assert "Unknown column" in errors[0]


def test_upload_not_excel() -> None:
    contents = XLSX_MIME + base64.b64encode(b"not an excel file").decode()
    _, errors = sub.parse_upload(contents, "a.xlsx")
    assert "not a valid Excel" in errors[0]


# ------------------------------------------------------------------ storage
def test_save_submission_writes_clean_workbook(submissions_dir: Path) -> None:
    rec, _ = sub.clean_record(valid_record(building_name='=HYPERLINK("http://x")'))
    sub_id = sub.save_submission([rec], "form", comment="hello")
    files = list(submissions_dir.glob("*.xlsx"))
    assert len(files) == 1
    assert files[0].name.startswith(sub_id)
    stored = pd.read_excel(files[0], sheet_name="buildings")
    assert stored.loc[0, "building_name"] == '=HYPERLINK("http://x")'  # stored as text, not as a formula
    info_sheet = pd.read_excel(files[0], sheet_name="submission_info", header=None)
    info = dict(info_sheet.itertuples(index=False, name=None))
    assert info["submission_id"] == sub_id
    assert info["comment"] == "hello"


# ------------------------------------------------------------------ anti-spam
def _solve(question: str) -> int:
    a, b = question.removeprefix("What is ").removesuffix("?").split(" + ")
    return int(a) + int(b)


def test_human_check(monkeypatch: pytest.MonkeyPatch) -> None:
    question, token = sub.new_challenge()
    assert sub.check_human(token, _solve(question), "") == "Please take a moment to check your entry before sending."
    later = time.time() + sub.MIN_SECONDS_ON_PAGE + 1
    monkeypatch.setattr(sub.time, "time", lambda: later)
    assert sub.check_human(token, _solve(question), "") is None
    assert sub.check_human(token, _solve(question) + 1, "") == "The answer to the anti-spam question is not correct."
    assert sub.check_human(token, "", "") == "Please answer the anti-spam question."
    assert sub.check_human(token, _solve(question), "filled by a bot") == "bot"
    assert sub.check_human(None, 1, "") == "The page has expired. Please reload it."


def test_expired_token(monkeypatch: pytest.MonkeyPatch) -> None:
    question, token = sub.new_challenge()
    later = time.time() + sub.TOKEN_MAX_AGE_S + 1
    monkeypatch.setattr(sub.time, "time", lambda: later)
    assert sub.check_human(token, _solve(question), "") == "The page has expired. Please reload it."


def test_rate_limit() -> None:
    client = f"test-client-{time.time()}"
    allowed = sub.RATE_LIMITS[0][1]
    assert not any(sub.rate_limited(client) for _ in range(allowed))
    assert sub.rate_limited(client)


def test_client_id_outside_request() -> None:
    assert sub.client_id() == "local"
