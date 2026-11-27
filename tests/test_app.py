"""Smoke tests of the Dash app: pages, layouts and the main callbacks run on the real dataset."""

from __future__ import annotations

import json
from typing import Any

import plotly.graph_objects as go
import pytest

from components.data import get_data

PAGES = {
    "/": "Dashboard",
    "/building": "Building detail",
    "/compare": "Compare smartness",
    "/contribute": "Contribute data",
    "/about": "About",
}


@pytest.fixture(scope="module")
def ids(dash_app: Any) -> list[str]:
    return list(get_data().buildings["building_id"])


def test_wsgi_entry_point(dash_app: Any) -> None:
    import app

    assert app.server is dash_app.server
    assert app.server.config["MAX_CONTENT_LENGTH"] > 0


def test_all_pages_registered(dash_app: Any) -> None:
    import dash

    registered = {p["path"]: p["name"] for p in dash.page_registry.values()}
    assert registered == PAGES


def test_layouts_build(dash_app: Any) -> None:
    from pages import about, building, compare, contribute, home

    for page in (home, building, compare, contribute, about):
        assert page.layout() is not None


def test_home_server_responds(dash_app: Any) -> None:
    client = dash_app.server.test_client()
    for path in PAGES:
        assert client.get(path).status_code == 200
    assert client.get("/_dash-layout").status_code == 200


def test_filter_without_filters_returns_all(ids: list[str]) -> None:
    from pages import home

    selected, text = home._filter([], [], [], [])
    assert selected == ids
    assert text.startswith(f"{len(ids)} of {len(ids)}")


def test_categorical_and_numeric_filters(ids: list[str]) -> None:
    from pages import home

    b = get_data().buildings
    country = b["country"].mode()[0]
    selected, _ = home._filter(["country"], [[country]], ["sri_total_pct"], [[0, 50]])
    expected = b[(b["country"] == country) & b["sri_total_pct"].between(0, 50)]["building_id"].tolist()
    assert selected == expected


def test_table_rows_are_json_without_nan(ids: list[str]) -> None:
    from pages import home

    rows = home._table(ids)
    assert len(rows) == len(ids)
    json.dumps(rows, allow_nan=False)  # NaN would break the browser grid


def test_kpis(ids: list[str]) -> None:
    from pages import home

    n, *_ = home._kpis(ids)
    assert n == str(len(ids))


def test_default_map_and_scatter_figures(ids: list[str]) -> None:
    from pages import home

    fig = home._map(ids, "sri_total_pct", "reference_year", "carto-positron", "Viridis")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0
    fig, _stats = home._scatter(ids, "reference_year", "sri_total_pct", "building_category", ["trend"])
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0


@pytest.mark.parametrize("color", [None, "building_category", "sbp_level", "validation_status"])
def test_map_colourings(ids: list[str], color: str | None) -> None:
    from pages import home

    assert isinstance(home._map(ids, None, color, "carto-positron", "Viridis"), go.Figure)


def test_every_building_page_renders(ids: list[str]) -> None:
    from pages import building

    for bid in ids:
        assert building._render(bid) is not None, bid


def test_unknown_building(ids: list[str]) -> None:
    from pages import building

    assert "not found" in str(building._render("NO-SUCH-ID"))


def test_compare_page(ids: list[str]) -> None:
    from pages import compare

    out = compare._compare(ids[:3])
    assert len(out) == 6
