"""Reconcile the processed model tables against the source publications.

Run after build_model.py:  python src/validate.py
Exits non-zero if any check fails.
"""
import sys

import pandas as pd

import config

P = config.PROCESSED
results: list[tuple[bool, str]] = []


def check(ok: bool, msg: str) -> None:
    results.append((bool(ok), msg))


def main() -> int:
    dim = pd.read_csv(P / "dim_local_authority.csv")
    region = pd.read_csv(P / "dim_region.csv")
    h = pd.read_csv(P / "fact_homelessness.csv", parse_dates=["quarter_end"])
    pub = pd.read_csv(P / "fact_homelessness_published.csv", parse_dates=["quarter_end"])
    lettings = pd.read_csv(P / "fact_lettings.csv", parse_dates=["year_end"])
    stock = pd.read_csv(P / "fact_prp_stock.csv", parse_dates=["as_at"])
    relets = pd.read_csv(P / "fact_relets_2025.csv")

    # --- dimensions -------------------------------------------------------------------
    check(len(dim) == 296 and dim["la_code"].is_unique, "296 unique councils in dim_local_authority")
    check(dim["la_code"].str.match(r"^E0[6-9]\d{6}$").all(), "all council codes are E06-E09")
    check(dim["is_london"].sum() == 33, "33 London councils")
    check(set(dim["region_code"]) <= set(region["region_code"]), "every council's region is in dim_region")
    for name, df in [("fact_homelessness", h), ("fact_lettings", lettings),
                     ("fact_prp_stock", stock), ("fact_relets_2025", relets)]:
        check(set(df["la_code"]) <= set(dim["la_code"]), f"{name}: all council codes in dim_local_authority")

    # --- homelessness -----------------------------------------------------------------
    quarters = h["quarter_end"].nunique()
    check(len(h) == quarters * 296, f"fact_homelessness: one row per council per quarter ({quarters} quarters)")
    check(not h.duplicated(["quarter_end", "la_code"]).any(), "fact_homelessness: no duplicate keys")
    check(not pub.duplicated(["quarter_end", "region_code"]).any(), "published totals: no duplicate keys")
    cols = ["households_in_ta", "children_in_ta", "owed_prevention_duty", "owed_relief_duty"]
    eng = pub[pub["region_code"] == "E92000001"].set_index("quarter_end")[cols]
    regs = pub[pub["region_code"].str.startswith("E12")].groupby("quarter_end")[cols].sum()
    # each region is rounded to the nearest 10 independently, so 9 regions can differ by up to 45
    gap = int((eng - regs).abs().max().max())
    check(gap <= 45, f"published regions sum to England every quarter (largest gap {gap}, rounding allows 45)")
    latest = eng.loc[pd.Timestamp("2026-03-31")]
    # Statutory homelessness in England: January to March 2026 (published 13 August 2026)
    check(latest["households_in_ta"] == 135_580, "England TA at 31 Mar 2026 = 135,580 (published)")
    check(latest["owed_prevention_duty"] + latest["owed_relief_duty"] == 83_850,
          "England owed a duty Jan to Mar 2026 = 83,850 (published)")
    la_sum = h.groupby("quarter_end")["households_in_ta"].sum()
    check((la_sum <= eng["households_in_ta"] + 10).all(),
          "council sums never exceed published England TA (gaps are non-returns, not double counts)")

    # --- lettings: totals survive harmonisation ----------------------------------------
    raw = pd.read_excel(config.raw_path(config.CORE_TENANCIES), sheet_name="Table_1d", header=4)
    raw = raw[raw.iloc[:, 0].astype(str).str.match(r"^\d{4}/\d{2}$")]
    raw_tot = raw.groupby(raw.iloc[:, 0])["Total"].sum()
    raw_tot.index = [pd.Timestamp(f"{int(y[:4]) + 1}-03-31") for y in raw_tot.index]
    ours = lettings.groupby("year_end")["lettings"].sum()
    check((ours - raw_tot).abs().max() == 0, "lettings by year match CORE Table 1d totals exactly")

    # --- housing association stock: council sums match the RSH England row -------------
    xl = pd.ExcelFile(config.raw_path(config.PRP_TREND))
    for k in range(1, 12):
        y = xl.parse(f"Y_{k}")
        e = y[y["LA code"] == "England"].iloc[0]
        year = pd.Timestamp(f"{2014 + k}-03-31")
        s = stock[stock["as_at"] == year]
        ok_units = s["total_social_units"].sum() == e["All Stock - ALL PRPS (LCHO LARGE ONLY)"]
        rent = s["gn_social_rent_total"].sum() / s["gn_social_rent_units"].sum()
        rent_gap = abs(rent / e["Average_GN_NET"] - 1)
        # Units match exactly every year. Rents in 2016-17 differ from RSH's England figure by
        # ~0.14% (a different averaging base in early returns), so allow 0.25%.
        check(ok_units and rent_gap < 0.0025,
              f"PRP {year.year}: units match RSH England row exactly; weighted Social Rent within "
              f"{rent_gap:.2%} (GBP {rent:.2f} vs {e['Average_GN_NET']:.2f})")

    # --- relets ------------------------------------------------------------------------
    check(len(relets) == 296 and relets["relets"].notna().all(), "relets: complete for all 296 councils")
    check((relets["relets"] <= relets["social_stock_1_april"]).all(), "relets never exceed social stock")

    for ok, msg in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {msg}")
    failed = sum(not ok for ok, _ in results)
    print(f"\n{len(results) - failed}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
