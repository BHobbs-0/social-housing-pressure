"""Clean the quarterly statutory homelessness (H-CLIC) detailed local authority tables.

The table layout changed several times between 2019 and 2026 (merged multi-row
headers, spacer columns, a new 'accessible' format from late 2025). Rather than
hard-coding column positions, each column is located by checks that must hold
whatever the layout:

* Table A1: total owed a duty = owed prevention duty + owed relief duty
* Table TA1: households in TA / households in area (thousands) = published rate per 1,000
"""
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

import config
from readers import CODE, to_number


def _locate(raw: pd.DataFrame):
    """Return (code column index, first data row index, data rows, hh-in-area column index)."""
    code_col = next(c for c in range(4) if raw[c].astype(str).str.match(CODE).sum() > 100)
    is_data = raw[code_col].astype(str).str.match(CODE)
    first = is_data.idxmax()
    # header text often has line breaks inside cells ("households\n in area")
    header = raw.loc[: first - 1].astype(str).apply(lambda s: s.str.replace(r"\s+", " ", regex=True))
    hh_cols = [
        c for c in raw.columns
        if header[c].str.contains("households in area", case=False, regex=False).any()
    ]
    if not hh_cols:
        raise ValueError("no 'households in area' column found")
    return code_col, raw[is_data], hh_cols[0]


def _numeric_cols(rows: pd.DataFrame, start: int, stop: int) -> list[int]:
    """Columns between start and stop that hold numbers for at least one data row."""
    return [c for c in range(start, stop) if to_number(rows[c]).notna().any()]


def parse_a1(raw: pd.DataFrame) -> pd.DataFrame:
    code_col, rows, hh_col = _locate(raw)
    seq = _numeric_cols(rows, code_col + 2, hh_col)
    eng = rows[rows[code_col] == "E92000001"].iloc[0]
    v = [to_number(pd.Series([eng[c]]))[0] for c in seq]
    # Find i where owed_total = prevention + relief. Relief sits 2 columns on when a
    # Section 21 'of which' column is between them. Figures are rounded to the nearest
    # 10 independently, so allow a 20-household rounding tolerance (prefer exact matches).
    match = None
    for tol in (0, 20):
        for i in range(len(seq) - 2):
            for gap in (2, 1):
                j = i + gap + 1
                if j < len(seq) and v[i] > 1000 and abs(v[i] - v[i + 1] - v[j]) <= tol:
                    match = (i, j)
                    break
            if match:
                break
        if match:
            break
    if not match:
        raise ValueError(f"A1: could not find prevention + relief = owed in {v}")
    i, j = match
    prev, relief = seq[i + 1], seq[j]
    total = seq[i - 1] if i >= 1 and v[i - 1] >= v[i] else None
    out = pd.DataFrame({
        "la_code": rows[code_col].values,
        "households_area_000": to_number(rows[hh_col]).values,
        "initial_assessments": to_number(rows[total]).values if total is not None else np.nan,
        "owed_prevention_duty": to_number(rows[prev]).values,
        "owed_relief_duty": to_number(rows[relief]).values,
    })
    return out


def parse_ta1(raw: pd.DataFrame) -> pd.DataFrame:
    code_col, rows, hh_col = _locate(raw)
    before = _numeric_cols(rows, code_col + 2, hh_col)
    after = _numeric_cols(rows, hh_col + 1, raw.shape[1])
    ta, rate, with_kids, kids = before[-1], after[0], after[1], after[2]
    eng = rows[rows[code_col] == "E92000001"].iloc[0]
    t, hh, r = (float(to_number(pd.Series([eng[c]]))[0]) for c in (ta, hh_col, rate))
    if abs(t / hh - r) > 0.01:
        raise ValueError(f"TA1: TA total / households != published rate ({t}/{hh} vs {r})")
    return pd.DataFrame({
        "la_code": rows[code_col].values,
        "households_in_ta": to_number(rows[ta]).values,
        "households_in_ta_with_children": to_number(rows[with_kids]).values,
        "children_in_ta": to_number(rows[kids]).values,
    })


def _dedupe(df: pd.DataFrame) -> pd.DataFrame:
    """London appears twice in each table (top summary and regional list). Drop exact
    repeats; if a code repeats with different values something is wrong, so fail."""
    out = df.drop_duplicates()
    if out["la_code"].duplicated().any():
        raise ValueError(f"conflicting rows for {out.loc[out['la_code'].duplicated(), 'la_code'].tolist()}")
    return out


def _sheet(xl: pd.ExcelFile, name: str) -> str:
    """Resolve a sheet name; some releases append an underscore (e.g. 'TA1_')."""
    for s in xl.sheet_names:
        if s.strip().rstrip("_") == name:
            return s
    raise ValueError(f"no sheet {name!r} in {xl.sheet_names}")


def parse_quarter(item) -> pd.DataFrame:
    """Parse one quarter's file, caching the result as CSV so reruns skip the slow .ods read."""
    quarter, url = item
    cache = config.INTERIM / "homelessness" / f"{quarter}.csv"
    if cache.exists():
        return _dedupe(pd.read_csv(cache, parse_dates=["quarter_end"]))
    path = config.raw_path(url)
    try:
        xl = pd.ExcelFile(path)
        a1 = _dedupe(parse_a1(xl.parse(_sheet(xl, "A1"), header=None)))
        ta1 = _dedupe(parse_ta1(xl.parse(_sheet(xl, "TA1"), header=None)))
    except Exception as e:
        raise RuntimeError(f"{quarter} ({path.name}): {e}") from None
    df = a1.merge(ta1, on="la_code", how="outer")
    df.insert(0, "quarter_end", pd.Timestamp(f"{quarter[:4]}-{quarter[4:]}-01") + pd.offsets.MonthEnd(0))
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache, index=False)
    return df


def load_all(workers: int = 2) -> pd.DataFrame:
    """All quarters, all geographies (England, regions and LAs) at their original codes."""
    with ProcessPoolExecutor(workers) as ex:
        futures = [ex.submit(parse_quarter, item) for item in config.HOMELESSNESS.items()]
    frames, errors = [], []
    for f in futures:
        try:
            frames.append(f.result())
        except Exception as e:
            errors.append(str(e))
    if errors:
        raise RuntimeError("Homelessness parsing failed:\n  " + "\n  ".join(errors))
    return pd.concat(frames, ignore_index=True)
