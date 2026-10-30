# Data model

All data is in `data/smart_buildings_dataset.xlsx`. The app reads it with `components/data.py::get_data()`.

## Sheets

| Sheet | One row per | Purpose |
|---|---|---|
| `README` | – | Short instructions inside the workbook |
| `buildings` | building | Identity, location, characteristics, SRI and SbP results |
| `sri_detailed` | building × technical domain × impact criterion | Detailed SRI matrix (long format: `building_id, domain, impact, score_pct`) |
| `data_dictionary` | column of `buildings` | Label, unit, group, type (dtype), description and hover flag |
| `sources` | reference | Bibliographic sources |

## Column groups in `buildings`

| Group | Examples |
|---|---|
| Identity | `building_id` (unique key), `short_name`, `building_name`, `owner_partner` |
| Location | `address`, `city`, `municipality`, `county`, `country`, `latitude`, `longitude`, `location_precision` |
| Building | `building_type`, `building_category`, `floor_area_category`, `floor_area_m2`, `construction_period`, `construction_year`, `latest_renovation_year`, `reference_year`, `reference_year_estimated`, `n_sri_domains_assessed`, `epc_label` |
| Building performance (26) | `performance_reference_year`, energy use intensities (`primary_energy_kwh_m2yr`, `final_energy_kwh_m2yr`, `electricity_use_kwh_m2yr`, …), demands and peak loads (`…_w_m2`), renewables and grid exchange, carbon (`operational_carbon_kgco2e_m2yr`, `embodied_carbon_kgco2e_m2`, `whole_life_carbon_kgco2e_m2` with `whole_life_carbon_study_period_years`, …), water, U-value, operating cost, occupant satisfaction. Intensities are per m² of conditioned floor area |
| SRI | `sri_total_pct`, `sri_class`, `sri_kf1_building_pct`, `sri_kf2_user_pct`, `sri_kf3_grid_pct` |
| SRI impact criteria (7) | `sri_impact_<energy_efficiency, energy_flexibility, comfort, convenience, health_wellbeing, maintenance, information>_pct` |
| SRI technical domains (9) | `sri_domain_<heating, dhw, cooling, ventilation, lighting, envelope, electricity, ev_charging, monitoring_control>_pct` |
| Smart by Powerhouse | `sbp_level`, `sbp_<topic>_level`, `sbp_<topic>_pct` for 5 topics |
| Metadata | `smartness_assessment_year`, `sri_method`, `sbp_tool`, `detail_available`, `notes` |
| References | `main_reference`, `main_reference_url`, `building_info_reference`, `building_info_reference_url`, `performance_info_reference`, `performance_info_reference_url` |

Units: percentages are 0–100; SbP levels range from −2 (no technological equipment) to 4 (smart cognitive).
An empty cell means *not available / not assessed* (e.g. a technical domain absent from the building).

## References

Each building has three references, each with an optional URL/DOI:

| Column | Meaning |
|---|---|
| `main_reference` | Main source of the information on the building (short citation). Used as a category filter and colour grouping |
| `building_info_reference` | Where the building characteristics come from (type, size, year, location) |
| `performance_info_reference` | Where the SRI / Smart by Powerhouse results come from |

The three may be identical. Full bibliographic entries are listed in the `sources` sheet.

## `data_dictionary` and the app dropdowns

Every column of `buildings` is offered in the app, according to its `dtype` in `data_dictionary`:

| dtype | Where it appears |
|---|---|
| `numeric` | Bubble size, bubble colour, X / Y axes, colour by, numeric filters, statistics cards |
| `categorical` / `text` | Bubble colour, colour by, category filters |

Parameters without any value yet are listed with "(no data yet)" and cannot be selected until a building has a value.
The `hover` column (`Y`) marks the parameters that are always shown in the map and plot hover pop-ups.

The `label`, `unit` and `description` of each row are shown as hover text (with the number of buildings that
have a value) on the parameter options of every dropdown and on the column headers of the data table.
Write the description so that a user unfamiliar with the frameworks understands what the parameter measures.

## Adding data

- **New building:** add a row to `buildings` with a unique `building_id` and `latitude`/`longitude`.
  Optionally add its detailed matrix rows to `sri_detailed`.
- **New parameter:** add a column to `buildings` and a row to `data_dictionary` (column name, label, unit,
  group, dtype, description, optional hover flag).
- Save, close Excel (the `~$` lock file is git-ignored), refresh the browser.
- **Contributions from users** arrive through the *Contribute data* page and are collected with
  `tools/fetch_submissions.py` (see [deployment.md](deployment.md)); review them, then copy accepted rows here.
  The form and the downloadable template are generated from this workbook, so new parameters appear there too.

## Current content

- 7 EDISON pilot buildings – SINTEF Notes, EDISON D1.1a SRI/SbP assessment (2026): full SRI and SbP detail.
- 10 municipal buildings in Ålesund (anonymised) – Campodonico Avendaño et al. (2024), *Energy and Buildings*
  314, 114234, and REHVA Journal 05/2024: SRI total, key functionalities, SbP level, year.

Map positions marked *approximate* or *anonymised* in `location_precision` are not exact building locations.
