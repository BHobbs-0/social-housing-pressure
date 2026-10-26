"""Paths and source URLs for the social housing supply and pressure pipeline.

All sources are official statistics published on GOV.UK under the
Open Government Licence v3.0.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"  # per-file parse cache, safe to delete
PROCESSED = ROOT / "data" / "processed"

ASSETS = "https://assets.publishing.service.gov.uk/media"

# Regulator of Social Housing: private registered provider (housing association) stock
PRP_TREND = f"{ASSETS}/68f8a6766a52e8a2726dc270/PRP_LA_TREND_TOOL_2015-25_FINAL_V1.0.xlsx"
PRP_GEO = f"{ASSETS}/68f8a6560794bb80118bb71f/GEO_PRP_TOOL_2025_FINAL_V1.0.xlsx"

# MHCLG: social housing lettings (CORE), 2024/25 release
CORE_TENANCIES = (
    f"{ASSETS}/69147610eba5bda2026fc827/"
    "Social_Housing_Lettings_in_England__Tenancies_Summary_Tables__2024-25.ods"
)

# MHCLG: statutory homelessness detailed local authority tables, one file per quarter.
# Key = quarter end (YYYYMM). Revised versions are used where published.
_H = "Statutory_Homelessness_Detailed_Local_Authority_Data"
HOMELESSNESS = {
    "201909": f"{ASSETS}/5ec53218e90e0754d1dedf18/DetailedLA_201909_revised.xlsx",
    "201912": f"{ASSETS}/5f749aaad3bf7f2868b3ffa2/DetailedLA_201912_revised.ods",
    "202003": f"{ASSETS}/65e6e8207bc329020bb8c266/Detailed_LA_202003_Revised_Fixed.ods",
    "202006": f"{ASSETS}/65e6e8372f2b3be8b07cd78e/Detailed_LA_202006_Revised_Fixed.ods",
    "202009": f"{ASSETS}/60803c88e90e076aab2a0531/DetailedLA_202009_Revised.ods",
    "202012": f"{ASSETS}/60fae728d3bf7f04599e2170/DetailedLA_202012_Revised_updated.ods",
    "202103": f"{ASSETS}/61796748e90e0719833464ff/DetailedLA_202103_Revised.ods",
    "202106": f"{ASSETS}/6a2c204ce50716856ed4b00e/DetailedLA_202106_revised_corrected.ods",
    "202109": f"{ASSETS}/62694963d3bf7f0e7121ae4b/DetailedLA_202109_revised.ods",
    "202112": f"{ASSETS}/62e14c208fa8f564a21dcd8a/Detailed_LA_202112_revised.ods",
    "202203": f"{ASSETS}/637e39e0d3bf7f153b8b321c/Detailed_LA_202203_revised.ods",
    "202206": f"{ASSETS}/6400d30c8fa8f527ff6b42db/Detailed_LA_202206_revised_Updated.ods",
    "202209": f"{ASSETS}/645a5900479612000cc29274/V2_Detailed_LA_202209_revised.ods",
    "202212": f"{ASSETS}/64be88f41e10bf000e17cd3a/Detailed_LA_202212_revised.ods",
    "202303": f"{ASSETS}/65804b3f83ba38000de1b77a/Detailed_LA_202303_Revised.ods",
    "202306": f"{ASSETS}/65df3f24cf7eb16adff57f55/Detailed_LA_202306_revised.ods",
    "202309": f"{ASSETS}/662f6dd89e82181baa98a8f5/Detailed_LA_202309_revised.ods",
    "202312": f"{ASSETS}/66b331c5a3c2a28abb50ddfd/Detailed_LA_202312_Revised_No_Dropdowns.ods",
    "202403": f"{ASSETS}/6747279da72d7eb7f348c04c/Detailed_LA_202403.xlsx",
    "202406": f"{ASSETS}/699d950a532c9ad91ebbcbd2/{_H}_202406_revised.ods",
    "202409": f"{ASSETS}/699d953607d7bff3604d6c0a/{_H}_202409_revised.ods",
    "202412": f"{ASSETS}/699d956edb2401de164d6c1c/{_H}_202412_revised.ods",
    "202503": f"{ASSETS}/699d95ae07d7bff3604d6c0c/{_H}_202503_revised.ods",
    "202506": f"{ASSETS}/6a2c1fe0e50716856ed4b008/Detailed_LA_202506_revised_corrected.xlsx",
    "202509": f"{ASSETS}/6a83027a3be22055c1aaa3c0/{_H}_202509_revised_accessible.ods",
    "202512": f"{ASSETS}/6a8302c63be22055c1aaa3c2/{_H}_202512_revised.ods",
    "202603": f"{ASSETS}/6a82eeb83bd75b81e2329a7a/{_H}_202603.ods",
}


def raw_path(url: str) -> Path:
    return RAW / url.rsplit("/", 1)[-1]
