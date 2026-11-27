"""Integrity of data/smart_buildings_dataset.xlsx (run after every data change)."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from components.data import (
    ASHRAE_ZONE_LABELS,
    DATA_FILE,
    VALIDATION_STATUS_VALUES,
    get_data,
    is_numeric,
)

SHEETS = ["README", "buildings", "sri_detailed", "data_dictionary", "sources"]
REQUIRED = [
    "building_id",
    "building_name",
    "country",
    "latitude",
    "longitude",
    "location_precision",
    "building_category",
    "main_reference",
    "validation_status",
]
DTYPES = {"numeric", "categorical", "text"}
SRI_CLASSES = [
    (90, "Class 1"),
    (80, "Class 2"),
    (65, "Class 3"),
    (50, "Class 4"),
    (35, "Class 5"),
    (20, "Class 6"),
    (0, "Class 7"),
]


@pytest.fixture(scope="module")
def buildings() -> pd.DataFrame:
    return get_data().buildings


@pytest.fixture(scope="module")
def dictionary() -> pd.DataFrame:
    return get_data().dictionary


def test_workbook_has_all_sheets() -> None:
    names = pd.ExcelFile(DATA_FILE).sheet_names
    assert set(SHEETS) <= set(names)


def test_building_ids_unique_and_present(buildings: pd.DataFrame) -> None:
    ids = buildings["building_id"]
    assert ids.notna().all()
    assert (ids.str.strip() == ids).all(), "building_id with leading/trailing spaces"
    dup = ids[ids.duplicated()].tolist()
    assert not dup, f"duplicate building_id: {dup}"


def test_required_columns_filled(buildings: pd.DataFrame) -> None:
    for col in REQUIRED:
        missing = buildings.loc[buildings[col].isna(), "building_id"].tolist()
        assert not missing, f"{col} is empty for {missing}"


def test_coordinates_in_range(buildings: pd.DataFrame) -> None:
    assert buildings["latitude"].between(-90, 90).all()
    assert buildings["longitude"].between(-180, 180).all()


def test_dictionary_matches_buildings_columns(buildings: pd.DataFrame, dictionary: pd.DataFrame) -> None:
    cols, described = set(buildings.columns), set(dictionary["column"])
    assert not cols - described, f"columns without a data_dictionary row: {sorted(cols - described)}"
    assert not described - cols, f"data_dictionary rows without a column: {sorted(described - cols)}"
    assert set(dictionary["dtype"]) <= DTYPES
    undescribed = dictionary.loc[dictionary["description"].isna(), "column"].tolist()
    assert not undescribed, f"columns without description: {undescribed}"


def test_numeric_columns_are_numbers(buildings: pd.DataFrame, dictionary: pd.DataFrame) -> None:
    for col in dictionary.loc[dictionary["dtype"] == "numeric", "column"]:
        values = buildings[col].dropna()
        converted = pd.to_numeric(values, errors="coerce")
        bad = buildings.loc[values.index[converted.isna()], "building_id"].tolist()
        assert not bad, f"{col}: non-numeric values for {bad}"
        assert is_numeric(col)


def test_sri_scores_in_range(buildings: pd.DataFrame) -> None:
    for col in [c for c in buildings.columns if c.startswith("sri_") and c.endswith("_pct")]:
        values = buildings[col].dropna()
        lo = -100 if ("domain" in col or "impact" in col or "kf" in col) else 0  # negative domain scores exist
        out = buildings.loc[values.index[~values.between(lo, 100)], "building_id"].tolist()
        assert not out, f"{col} outside {lo}…100 for {out}"


def test_sri_class_matches_total(buildings: pd.DataFrame) -> None:
    both = buildings.dropna(subset=["sri_total_pct", "sri_class"])
    for _, r in both.iterrows():
        expected = next(name for lo, name in SRI_CLASSES if r["sri_total_pct"] >= lo)
        assert str(r["sri_class"]).startswith(expected), (
            f"{r['building_id']}: {r['sri_class']} vs {r['sri_total_pct']} %"
        )


def test_years_plausible(buildings: pd.DataFrame) -> None:
    last = dt.date.today().year + 5
    for col in ["construction_year", "latest_renovation_year", "reference_year"]:
        values = buildings[col].dropna()
        assert values.between(1700, last).all(), f"{col} outside 1700…{last}"
    both = buildings.dropna(subset=["construction_year", "latest_renovation_year"])
    early = both.loc[both["latest_renovation_year"] < both["construction_year"], "building_id"].tolist()
    assert not early, f"renovation before construction: {early}"


def test_controlled_vocabularies(buildings: pd.DataFrame) -> None:
    zones = buildings["ashrae_climate_zone"].dropna()
    assert zones.isin(ASHRAE_ZONE_LABELS).all(), sorted(set(zones) - set(ASHRAE_ZONE_LABELS))
    assert buildings["validation_status"].isin(VALIDATION_STATUS_VALUES).all()


def test_country_level_positions_have_no_climate_zone(buildings: pd.DataFrame) -> None:
    country_only = buildings[buildings["location_precision"] == "Anonymised (country only)"]
    assert country_only["ashrae_climate_zone"].isna().all()


def test_text_values_trimmed(buildings: pd.DataFrame, dictionary: pd.DataFrame) -> None:
    for col in dictionary.loc[dictionary["dtype"] == "categorical", "column"]:
        values = buildings[col].dropna().astype(str)
        bad = values[values != values.str.strip()].tolist()
        assert not bad, f"{col}: values with leading/trailing spaces {bad}"


def test_sources_unique() -> None:
    sources = get_data().sources
    assert sources["source_id"].is_unique
    assert sources["reference"].notna().all()


def test_detailed_matrix_refers_to_known_buildings(buildings: pd.DataFrame) -> None:
    detailed = get_data().detailed
    unknown = set(detailed["building_id"].astype(str)) - set(buildings["building_id"])
    assert not unknown, f"sri_detailed rows for unknown buildings: {sorted(unknown)}"
