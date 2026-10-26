# Data dictionary

All tables are in `data/processed/`. Codes are ONS GSS codes on April 2024 local authority boundaries (296 councils). Money is pounds per week.

## Dimensions

### dim_local_authority (296 rows, one per council)

| Column | Description |
|---|---|
| la_code | GSS code, e.g. `E09000025` (key) |
| la_name | Council name |
| region_code, region_name | Region the council sits in (relate via `region_code`; slice with `dim_region`) |
| la_type | Unitary authority, District council, Metropolitan borough or London borough |
| is_london | True for the 33 London boroughs (incl. City of London) |
| households_000_latest | Households in the area, thousands, from the latest homelessness release (used as the denominator for supply rates) |
| map_location | `"<name>, England, United Kingdom"` for map visuals |

### dim_region (10 rows)

Nine English regions plus an `England` row (`is_england_total = True`). The England row exists so published national totals can be read; filter it out of region slicers.

### dim_date (daily, 1 Apr 2009 to 31 Dec 2026)

Calendar and UK financial year (April to March) attributes: `financial_year` ("2024/25"), `fiscal_quarter`, `quarter_label` ("Jan to Mar 2026"), sort columns, and quarter and year-end flags.

## Facts

### fact_homelessness (quarterly, by council, Jul to Sep 2019 to Jan to Mar 2026)

Source: MHCLG statutory homelessness detailed local authority tables A1 and TA1.

| Column | Description | Type |
|---|---|---|
| quarter_end | Last day of the quarter | |
| households_area_000 | Households in the area, thousands | snapshot |
| initial_assessments | Households assessed for a homelessness duty in the quarter | flow |
| owed_prevention_duty | Assessed as threatened with homelessness (prevention duty) | flow |
| owed_relief_duty | Assessed as already homeless (relief duty) | flow |
| households_in_ta | Households in temporary accommodation at quarter end | snapshot |
| households_in_ta_with_children | Of which, households with children | snapshot |
| children_in_ta | Children in those households | snapshot |

Blank = the council did not submit that quarter (shown as `..` in the source). For merged councils, a quarter is blank unless every predecessor council submitted.

### fact_homelessness_published (quarterly, England and 9 regions)

Same columns, keyed by `region_code`. These are MHCLG's published totals, which **include estimates for councils that did not submit**, so they are the right source for national and regional headline figures. Regions sum exactly to England.

### fact_lettings (annual, by council, 2009/10 to 2024/25)

Source: CORE social housing lettings, Table 1d. Long format, one row per council, year and category.

| Column | Values |
|---|---|
| year_end | 31 March of the financial year |
| rent_type | Social Rent, Affordable Rent, Intermediate Rent |
| needs_type | General Needs, Supported Housing |
| provider_type | Local authority, Housing association (PRP) |
| lettings | New lettings |

These are the council-level figures as published, without the national weighting MHCLG applies for missing returns, so the 2024/25 total (252,917) is a little below the headline national estimate (about 263,000).

### fact_prp_stock (annual at 31 March, by council, 2015 to 2025)

Source: Regulator of Social Housing, PRP local authority trend tool (Statistical Data Return). Housing associations only; council-owned stock is not included.

| Column | Description |
|---|---|
| as_at | 31 March of the year |
| gn_self_contained_units, gn_bedspaces, supported_housing_units, older_people_units | Owned stock by type |
| shared_ownership_units | Low cost home ownership (large providers only) |
| total_social_units | All social stock owned |
| low_cost_rental_units | Rental stock |
| decent_homes_fails | Rental homes failing the Decent Homes Standard |
| gn_social_rent_units, gn_social_rent_total | General needs Social Rent homes, and units x average net rent (for weighted averages) |
| gn_affordable_rent_units, gn_affordable_rent_total | Same for Affordable Rent |
| large_prp_gn_units, vacant_total, vacant_available_to_let | Large-provider general needs stock and vacancies |

### fact_relets_2025 (one row per council, 2024/25)

Source: CORE social housing lettings, Table 1e. Not related to `dim_date`.

| Column | Description |
|---|---|
| social_stock_1_april | All social homes (council plus housing association) at 1 April 2024 |
| relets | Social homes re-let in 2024/25 |
| avg_relet_rent, avg_market_rent | Average weekly rents |
| relet_rent_total | avg_relet_rent x relets |
| relets_with_market_rent, market_rent_total, relet_rent_total_market_matched | Weights for market comparisons, zero where no market rent is published (Barnsley, Sheffield, City of London, Isles of Scilly) |

## Geography harmonisation

Councils that merged between 2009 and 2023 (for example Buckinghamshire 2020, North and West Northamptonshire 2021, Cumberland, Westmorland and Furness, North Yorkshire and Somerset 2023) are mapped to their successor, with counts summed. Code-only changes (Gateshead, Northumberland, four Hertfordshire districts, and Barnsley and Sheffield in 2024) are recoded. The mapping is in `src/geography.py`; the pipeline stops with an error if it meets a code it can't map.
