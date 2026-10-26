"""Spreadsheet reading helpers shared by the cleaning modules."""
import re
import warnings

import pandas as pd
from pandas.io.excel import _odfreader

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

# Some GOV.UK .ods files contain cells of office:value-type="error" (a #N/A or #DIV/0!
# saved in a formula cell). pandas raises on these; treat them as missing instead.
_original_get_cell_value = _odfreader.ODFReader._get_cell_value


def _tolerant_get_cell_value(self, cell):
    from odf.namespaces import OFFICENS

    if cell.attributes.get((OFFICENS, "value-type")) == "error":
        return float("nan")
    return _original_get_cell_value(self, cell)


_odfreader.ODFReader._get_cell_value = _tolerant_get_cell_value

CODE = re.compile(r"^E\d{8}$")


def read_raw(path, sheet: str) -> pd.DataFrame:
    """Read a sheet with no header inference."""
    return pd.read_excel(path, sheet_name=sheet, header=None)


def to_number(s: pd.Series) -> pd.Series:
    """Convert to numbers; GOV.UK suppression markers ('..', '[x]', '[c]', '-') become NaN."""
    return pd.to_numeric(s, errors="coerce")
