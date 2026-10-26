"""Clean the Regulator of Social Housing PRP local authority trend tool, 2015 to 2025.

The workbook holds one hidden sheet per year (Y_1 = 2015 ... Y_11 = 2025), each
already on current local authority boundaries. Figures are as at 31 March.
"""
import pandas as pd

import config
from readers import to_number

FIRST_YEAR = 2015

COLUMNS = {
    "GNSC - ALL PRPS": "gn_self_contained_units",
    "GNBSPs  - ALL PRPS": "gn_bedspaces",
    "SH - ALL PRPS": "supported_housing_units",
    "HOP - ALL PRPS": "older_people_units",
    "LCHO <100% Equity LARGE ONLY": "shared_ownership_units",
    "All Stock - ALL PRPS (LCHO LARGE ONLY)": "total_social_units",
    "Rental Stock Total - ALL PRPS": "low_cost_rental_units",
    "DHS_Fails - ALL PRPS": "decent_homes_fails",
    "Average_GN_NET": "avg_gn_social_net_rent",
    "GN_SOCIAL RENT_UNIT_COUNT (EXCLUDES AR)": "gn_social_rent_units",
    "GN_Aff_Rnt": "avg_gn_affordable_rent",
    "Tot_GN_Aff_Rnt_Units": "gn_affordable_rent_units",
    "NEW Large PRP - GN SC stock": "large_prp_gn_units",
    "SU065_LA_Vac_avail_GN_SC": "vacant_available_to_let",
    "SU067_Tot_vac_GN_SC": "vacant_total",
}


def stock_trend() -> pd.DataFrame:
    path = config.raw_path(config.PRP_TREND)
    xl = pd.ExcelFile(path)
    frames = []
    for k in range(1, 12):
        df = xl.parse(f"Y_{k}")
        missing = set(COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(f"PRP trend Y_{k}: missing columns {missing}")
        df = df[df["LA code"].astype(str).str.match(r"^E0[6-9]\d{6}$")]
        out = df[list(COLUMNS)].rename(columns=COLUMNS).apply(to_number)
        out.insert(0, "la_code", df["LA code"].values)
        out.insert(0, "as_at", pd.Timestamp(f"{FIRST_YEAR + k - 1}-03-31"))
        frames.append(out)
    df = pd.concat(frames, ignore_index=True)
    # rent totals so Power BI can compute unit-weighted averages across areas
    df["gn_social_rent_total"] = df["avg_gn_social_net_rent"] * df["gn_social_rent_units"]
    df["gn_affordable_rent_total"] = df["avg_gn_affordable_rent"] * df["gn_affordable_rent_units"]
    return df.drop(columns=["avg_gn_social_net_rent", "avg_gn_affordable_rent"])
