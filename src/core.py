"""Clean CORE social housing lettings tables (MHCLG, 2024/25 release).

Table 1d: new lettings by local authority, 2009/10 to 2024/25 (tidied to long format)
Table 1e: churn, relet rents and market rents by local authority, 2024/25
"""
import re

import pandas as pd

import config
from readers import to_number

LETTING_COL = re.compile(r"^(SR|AR|IR) (General Needs|Supported Housing) (LA|PRP)")
RENT_TYPE = {"SR": "Social Rent", "AR": "Affordable Rent", "IR": "Intermediate Rent"}
PROVIDER = {"LA": "Local authority", "PRP": "Housing association (PRP)"}


def _name_key(names: pd.Series) -> pd.Series:
    """Normalise council names so spelling variants match ("Kings Lynn" / "King's Lynn",
    "St. Edmundsbury" / "St Edmundsbury", "Scilly, Isles of" / "Isles of Scilly")."""
    k = names.astype(str).str.lower().str.replace(r"[\'’.]", "", regex=True).str.strip()
    return k.replace({"scilly, isles of": "isles of scilly"})


def _fin_year_end(label: str) -> pd.Timestamp:
    """'2024/25' -> 2025-03-31"""
    return pd.Timestamp(f"{int(label[:4]) + 1}-03-31")


def lettings_by_la() -> pd.DataFrame:
    path = config.raw_path(config.CORE_TENANCIES)
    df = pd.read_excel(path, sheet_name="Table_1d", header=4)
    df = df.rename(columns={
        df.columns[0]: "financial_year",
        df.columns[3]: "la_code",
        df.columns[4]: "la_name",
    })
    df = df[df["financial_year"].astype(str).str.match(r"^\d{4}/\d{2}$")]

    # 2009/10 to 2010/11 use pre-2011 ONS codes (e.g. '19UH'). Map those to GSS codes by
    # council name, using names that appear against GSS codes in later years.
    gss = df["la_code"].str.match(r"^E\d{8}$")
    key = _name_key(df["la_name"])
    name_to_code = (
        df[gss].assign(key=key).drop_duplicates("key", keep="first").set_index("key")["la_code"]
    )
    old = ~gss
    df.loc[old, "la_code"] = key[old].map(name_to_code)
    unmatched = df.loc[old & df["la_code"].isna(), "la_name"].unique()
    if len(unmatched):
        raise ValueError(f"CORE Table 1d: no GSS code for {sorted(unmatched)}")

    value_cols = [c for c in df.columns if LETTING_COL.match(c)]
    long = df.melt(
        id_vars=["financial_year", "la_code"], value_vars=value_cols,
        var_name="category", value_name="lettings",
    )
    parts = long["category"].str.extract(LETTING_COL)
    long["rent_type"] = parts[0].map(RENT_TYPE)
    long["needs_type"] = parts[1]
    long["provider_type"] = parts[2].map(PROVIDER)
    long["lettings"] = to_number(long["lettings"])
    long["year_end"] = long["financial_year"].map(_fin_year_end)
    return long[["year_end", "la_code", "rent_type", "needs_type", "provider_type", "lettings"]]


def churn_and_rents() -> pd.DataFrame:
    """LA snapshot for 2024/25. Rent averages are turned into totals (avg x re-lets)
    so that Power BI can build correctly weighted regional and national averages."""
    path = config.raw_path(config.CORE_TENANCIES)
    df = pd.read_excel(path, sheet_name="Table_1e", header=4)
    c = list(df.columns)
    out = pd.DataFrame({
        "year_end": pd.Timestamp("2025-03-31"),
        "region_code": df[c[0]],
        "region_name": df[c[1]],
        "la_code": df[c[2]],
        "la_name": df[c[3]].str.strip(),
        "avg_relet_rent": to_number(df[c[4]]),
        "avg_market_rent": to_number(df[c[5]]),
        "relets": to_number(df[c[7]]),
        "social_stock_1_april": to_number(df[c[8]]),
    })
    out = out[out["la_code"].astype(str).str.match(r"^E0[6-9]\d{6}$")]
    out["relet_rent_total"] = out["avg_relet_rent"] * out["relets"]
    # A few councils have no published market rent. Market comparisons are weighted only
    # over re-lets where both rents exist, so those councils don't drag the ratio down.
    has_market = out["avg_market_rent"].notna()
    out["relets_with_market_rent"] = out["relets"].where(has_market, 0)
    out["market_rent_total"] = (out["avg_market_rent"] * out["relets"]).where(has_market, 0)
    out["relet_rent_total_market_matched"] = out["relet_rent_total"].where(has_market, 0)
    return out
