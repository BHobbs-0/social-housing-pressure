"""Build the Power BI model tables (star schema) as CSVs in data/processed/.

Run from the repository root:
    python src/build_model.py            # downloads anything missing, then builds
    python src/build_model.py --no-download

Outputs
    dim_local_authority.csv       one row per current English local authority (296)
    dim_region.csv                9 English regions plus an England row
    dim_date.csv                  daily calendar with financial year and quarter labels
    fact_homelessness.csv         quarterly H-CLIC duties and temporary accommodation by LA
    fact_homelessness_published.csv  published England and regional totals (these include
                                  MHCLG estimates for councils that did not submit data)
    fact_lettings.csv             new social lettings by LA, year, rent, needs and provider type
    fact_prp_stock.csv            housing association stock, rents and vacancies by LA, 2015-2025
    fact_relets_2025.csv          2024/25 re-lets, churn and relet vs market rent by LA
"""
import argparse
import sys

import pandas as pd

import config
import core
import download
import geography
import homelessness
import prp

LA = r"^E0[6-9]\d{6}$"


def build_dim_local_authority(relets: pd.DataFrame, hless: pd.DataFrame) -> pd.DataFrame:
    dim = relets[["la_code", "la_name", "region_code", "region_name"]].copy()
    dim["la_type"] = dim["la_code"].map(geography.la_type)
    dim["is_london"] = dim["region_name"].eq("London")
    latest = hless[hless["quarter_end"] == hless["quarter_end"].max()]
    dim = dim.merge(
        latest[["la_code", "households_area_000"]].rename(columns={"households_area_000": "households_000_latest"}),
        on="la_code", how="left",
    )
    # Power BI map visuals geocode more reliably with a country suffix
    dim["map_location"] = dim["la_name"] + ", England, United Kingdom"
    return dim.sort_values(["region_name", "la_name"]).reset_index(drop=True)


def build_dim_date(start="2009-04-01", end="2026-12-31") -> pd.DataFrame:
    d = pd.DataFrame({"date": pd.date_range(start, end, freq="D")})
    fy_start = d["date"].dt.year - (d["date"].dt.month < 4).astype(int)
    d["year"] = d["date"].dt.year
    d["month_number"] = d["date"].dt.month
    d["month_name"] = d["date"].dt.strftime("%b")
    d["calendar_quarter"] = d["year"].astype(str) + " Q" + d["date"].dt.quarter.astype(str)
    q_start = d["date"].dt.to_period("Q").dt.start_time
    d["quarter_label"] = q_start.dt.strftime("%b") + " to " + (q_start + pd.offsets.QuarterEnd(0)).dt.strftime("%b %Y")
    d["quarter_sort"] = d["year"] * 10 + d["date"].dt.quarter
    d["financial_year"] = fy_start.astype(str) + "/" + (fy_start + 1).astype(str).str[-2:]
    d["financial_year_sort"] = fy_start
    d["fiscal_quarter"] = "Q" + (((d["month_number"] - 4) % 12) // 3 + 1).astype(str)
    d["is_quarter_end"] = d["date"].eq(d["date"] + pd.offsets.QuarterEnd(0))
    d["is_financial_year_end"] = (d["month_number"] == 3) & (d["date"].dt.day == 31)
    return d


def build_homelessness(raw: pd.DataFrame, valid: set[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    values = [
        "households_area_000", "initial_assessments", "owed_prevention_duty", "owed_relief_duty",
        "households_in_ta", "households_in_ta_with_children", "children_in_ta",
    ]
    # Published England and regional totals include MHCLG estimates for councils that did not
    # submit that quarter, so they are kept separately for headline figures.
    published = raw[raw["la_code"].astype(str).str.match(r"^E(92|12)\d{6}$")]
    published = published.rename(columns={"la_code": "region_code"})[["quarter_end", "region_code"] + values]
    las = raw[raw["la_code"].astype(str).str.match(LA)]
    fact = geography.harmonise(las, ["quarter_end"], values, valid)
    return fact, published.reset_index(drop=True)


def build_dim_region(relets: pd.DataFrame) -> pd.DataFrame:
    dim = relets[["region_code", "region_name"]].drop_duplicates().sort_values("region_name")
    england = pd.DataFrame({"region_code": ["E92000001"], "region_name": ["England"]})
    dim = pd.concat([dim, england], ignore_index=True)
    dim["is_england_total"] = dim["region_code"].eq("E92000001")
    return dim


def _whole_numbers_as_int(df: pd.DataFrame) -> pd.DataFrame:
    """Counts with gaps are floats in pandas ('123.0'); write them as nullable integers instead."""
    df = df.copy()
    for c in df.select_dtypes("float").columns:
        s = df[c].dropna()
        if len(s) and (s == s.round()).all() and not c.endswith(("_000", "_total", "_rent")):
            df[c] = df[c].astype("Int64")
        else:
            df[c] = df[c].round(4)  # tidy float noise such as 354438.98000000004
    return df


def build(no_download: bool = False) -> int:
    if not no_download and download.main() != 0:
        print("Some downloads failed; continuing with files already present.", file=sys.stderr)

    print("Reading CORE lettings ...")
    relets = core.churn_and_rents()
    relets["la_code"] = relets["la_code"].map(geography.to_current)
    valid = set(relets["la_code"])
    lettings = geography.harmonise(
        core.lettings_by_la(), ["year_end", "rent_type", "needs_type", "provider_type"], ["lettings"], valid
    )

    print("Reading housing association (PRP) stock ...")
    stock = prp.stock_trend()
    stock["la_code"] = stock["la_code"].map(geography.to_current)  # already on current boundaries; recode only
    unknown = set(stock["la_code"]) - valid
    if unknown:
        raise ValueError(f"PRP trend tool has LA codes not in the current list: {unknown}")

    print("Reading homelessness quarters (slow the first time; cached afterwards) ...")
    hless_raw = homelessness.load_all()
    hless, hless_published = build_homelessness(hless_raw, valid)

    tables = {
        "dim_local_authority": build_dim_local_authority(relets, hless),
        "dim_region": build_dim_region(relets),
        "dim_date": build_dim_date(),
        "fact_homelessness": hless,
        "fact_homelessness_published": hless_published,
        "fact_lettings": lettings,
        "fact_prp_stock": stock,
        "fact_relets_2025": relets.drop(columns=["la_name", "region_code", "region_name"]),
    }
    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df = _whole_numbers_as_int(df)
        df.to_csv(config.PROCESSED / f"{name}.csv", index=False, date_format="%Y-%m-%d")
        print(f"  wrote {name}.csv  {df.shape[0]:>7,} rows x {df.shape[1]} cols")

    print("\nValidating against source publications ...")
    import validate
    return validate.main()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-download", action="store_true", help="use files already in data/raw")
    sys.exit(build(ap.parse_args().no_download))
