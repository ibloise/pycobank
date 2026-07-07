"""Constants and public package metadata for PycoBank."""

from __future__ import annotations

PACKAGE_VERSION = "0.1.0"

DEFAULT_MYCOBANK_URL = "https://www.mycobank.org/images/MBList.zip"
DEFAULT_TABLE = "mycobank"
DEFAULT_SHEET = "Sheet1"
DEFAULT_CACHE_DIR_NAME = "mycobank"
DEFAULT_ZIP_NAME = "MBList.zip"
DEFAULT_EXCEL_FILE = "MBList.xlsx"
DEFAULT_USER_AGENT = "Mozilla/5.0 PycoBank/0.1"

CORE_COLUMNS = (
    "id",
    "taxon_name",
    "authors",
    "authors_abbreviated",
    "rank",
    "year_of_effective_publication",
    "name_status",
    "mycobank",
    "hyperlink_to_mb",
    "classification",
    "current_mycobank",
    "current_name",
    "synonymy",
)

SUMMARY_COLUMNS = (
    "id",
    "taxon_name",
    "rank",
    "name_status",
    "mycobank",
    "current_mycobank",
    "current_name",
    "classification",
    "synonymy",
)
