"""Local authority geography: harmonise historic LA codes to the April 2024 (current) boundaries.

Several English councils merged between 2009 and 2023, and Barnsley and Sheffield
changed codes in 2024. Every source table is mapped to current codes so that time
series line up. Counts are summed across the predecessor councils; rates are always
recalculated from those summed counts.
"""
import re

import pandas as pd

LA_CODE = re.compile(r"^E0[6-9]\d{6}$")

# old code -> successor code. Chains (e.g. 2019 -> 2023) are resolved by to_current().
SUCCESSORS = {
    # 2012-2013 code changes (no boundary change, new code)
    "E07000100": "E07000240",  # St Albans
    "E07000104": "E07000241",  # Welwyn Hatfield
    "E07000097": "E07000242",  # East Hertfordshire
    "E07000101": "E07000243",  # Stevenage
    "E08000020": "E08000037",  # Gateshead
    "E06000048": "E06000057",  # Northumberland
    # April 2019
    "E06000028": "E06000058",  # Bournemouth -> Bournemouth, Christchurch and Poole
    "E06000029": "E06000058",  # Poole -> BCP
    "E07000048": "E06000058",  # Christchurch -> BCP
    "E07000049": "E06000059",  # East Dorset -> Dorset
    "E07000050": "E06000059",  # North Dorset -> Dorset
    "E07000051": "E06000059",  # Purbeck -> Dorset
    "E07000052": "E06000059",  # West Dorset -> Dorset
    "E07000053": "E06000059",  # Weymouth and Portland -> Dorset
    "E07000201": "E07000245",  # Forest Heath -> West Suffolk
    "E07000204": "E07000245",  # St Edmundsbury -> West Suffolk
    "E07000205": "E07000244",  # Suffolk Coastal -> East Suffolk
    "E07000206": "E07000244",  # Waveney -> East Suffolk
    "E07000190": "E07000246",  # Taunton Deane -> Somerset West and Taunton
    "E07000191": "E07000246",  # West Somerset -> Somerset West and Taunton
    # April 2020
    "E07000004": "E06000060",  # Aylesbury Vale -> Buckinghamshire
    "E07000005": "E06000060",  # Chiltern
    "E07000006": "E06000060",  # South Bucks
    "E07000007": "E06000060",  # Wycombe
    # April 2021
    "E07000150": "E06000061",  # Corby -> North Northamptonshire
    "E07000152": "E06000061",  # East Northamptonshire
    "E07000153": "E06000061",  # Kettering
    "E07000156": "E06000061",  # Wellingborough
    "E07000151": "E06000062",  # Daventry -> West Northamptonshire
    "E07000154": "E06000062",  # Northampton
    "E07000155": "E06000062",  # South Northamptonshire
    # April 2023
    "E07000026": "E06000063",  # Allerdale -> Cumberland
    "E07000028": "E06000063",  # Carlisle
    "E07000029": "E06000063",  # Copeland
    "E07000027": "E06000064",  # Barrow-in-Furness -> Westmorland and Furness
    "E07000030": "E06000064",  # Eden
    "E07000031": "E06000064",  # South Lakeland
    "E07000163": "E06000065",  # Craven -> North Yorkshire
    "E07000164": "E06000065",  # Hambleton
    "E07000165": "E06000065",  # Harrogate
    "E07000166": "E06000065",  # Richmondshire
    "E07000167": "E06000065",  # Ryedale
    "E07000168": "E06000065",  # Scarborough
    "E07000169": "E06000065",  # Selby
    "E07000187": "E06000066",  # Mendip -> Somerset
    "E07000188": "E06000066",  # Sedgemoor
    "E07000189": "E06000066",  # South Somerset
    "E07000246": "E06000066",  # Somerset West and Taunton
    # April 2024: minor boundary change, new codes
    "E08000016": "E08000038",  # Barnsley
    "E08000019": "E08000039",  # Sheffield
}


def to_current(code: str) -> str:
    seen = set()
    while code in SUCCESSORS and code not in seen:
        seen.add(code)
        code = SUCCESSORS[code]
    return code


def la_type(code: str) -> str:
    return {
        "E06": "Unitary authority",
        "E07": "District council",
        "E08": "Metropolitan borough",
        "E09": "London borough",
    }.get(code[:3], "Other")


def _sum_all_or_nan(s: pd.Series):
    """Sum only when every predecessor reported; a partial sum would understate the merged area."""
    return s.sum() if s.notna().all() else float("nan")


def harmonise(df: pd.DataFrame, keys: list[str], value_cols: list[str], valid_codes: set[str]) -> pd.DataFrame:
    """Map la_code to current geography and aggregate count columns.

    Raises if any code cannot be mapped to a current authority, so a new
    boundary change stops the run instead of quietly dropping rows.
    """
    df = df.copy()
    df["la_code"] = df["la_code"].map(to_current)
    unknown = sorted(set(df["la_code"]) - valid_codes)
    if unknown:
        raise ValueError(f"LA codes with no current equivalent: {unknown}")
    return df.groupby(keys + ["la_code"], as_index=False)[value_cols].agg(_sum_all_or_nan)
