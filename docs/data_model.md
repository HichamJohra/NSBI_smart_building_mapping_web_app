# Data model

All data is in `data/smart_buildings_dataset.xlsx`. The app reads it with `components/data.py::get_data()`.

## Sheets

| Sheet | One row per | Purpose |
|---|---|---|
| `README` | – | Short instructions inside the workbook |
| `buildings` | building | Identity, location, characteristics, SRI and SbP results |
| `sri_detailed` | building × technical domain × impact criterion | Detailed SRI matrix (long format: `building_id, domain, impact, score_pct`) |
| `data_dictionary` | column of `buildings` | Label, unit, group, type, description and dropdown flags |
| `sources` | reference | Bibliographic sources |

## Column groups in `buildings`

| Group | Examples |
|---|---|
| Identity | `building_id` (unique key), `short_name`, `building_name`, `owner_partner`, `source_study`, `project` |
| Location | `address`, `city`, `municipality`, `county`, `country`, `latitude`, `longitude`, `location_precision` |
| Building | `building_type`, `building_category`, `floor_area_category`, `floor_area_m2`, `construction_period`, `construction_year`, `latest_renovation_year`, `reference_year`, `reference_year_estimated`, `n_sri_domains_assessed`, `epc_label` |
| SRI | `sri_total_pct`, `sri_class`, `sri_kf1_building_pct`, `sri_kf2_user_pct`, `sri_kf3_grid_pct` |
| SRI impact criteria (7) | `sri_impact_<energy_efficiency, energy_flexibility, comfort, convenience, health_wellbeing, maintenance, information>_pct` |
| SRI technical domains (9) | `sri_domain_<heating, dhw, cooling, ventilation, lighting, envelope, electricity, ev_charging, monitoring_control>_pct` |
| Smart by Powerhouse | `sbp_level`, `sbp_<topic>_level`, `sbp_<topic>_pct` for 5 topics |
| Metadata | `assessment_year`, `sri_method`, `sbp_tool`, `detail_available`, `reference`, `reference_url`, `notes` |

Units: percentages are 0–100; SbP levels range from −2 (no technological equipment) to 4 (smart cognitive).
An empty cell means *not available / not assessed* (e.g. a technical domain absent from the building).

## `data_dictionary` flags

Put `Y` in a flag column to make a `buildings` column appear in the corresponding control:

| Flag | Where it appears |
|---|---|
| `map_size` | "Bubble size" dropdown (numeric only) |
| `map_color` | "Bubble colour" and "Colour by" dropdowns (numeric or categorical) |
| `xy` | X and Y axis dropdowns of the correlation explorer (numeric only) |
| `filter` | Numeric range filters / category filter |
| `hover` | Always shown in the map and plot hover pop-ups |

Columns without any value are hidden automatically until data is added.

## Adding data

- **New building:** add a row to `buildings` with a unique `building_id` and `latitude`/`longitude`.
  Optionally add its detailed matrix rows to `sri_detailed`.
- **New parameter:** add a column to `buildings` and a row to `data_dictionary` (column name, label, unit,
  group, dtype, flags).
- Save, close Excel (the `~$` lock file is git-ignored), refresh the browser.

## Current content

- 7 EDISON pilot buildings – SINTEF Notes, EDISON D1.1a SRI/SbP assessment (2026): full SRI and SbP detail.
- 10 municipal buildings in Ålesund (anonymised) – Campodonico Avendaño et al. (2024), *Energy and Buildings*
  314, 114234, and REHVA Journal 05/2024: SRI total, key functionalities, SbP level, year.

Map positions marked *approximate* or *anonymised* in `location_precision` are not exact building locations.
