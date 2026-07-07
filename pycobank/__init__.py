"""Python tools for building and querying a local MycoBank MBList database."""

from __future__ import annotations

from .builder import build_database
from .client import (
    PycoBank,
    MycoBank,
    PycoBankError,
    UnknownColumn,
)
from .contracts import DEFAULT_MYCOBANK_URL, PACKAGE_VERSION
from .models import MycoBankRecord, Synonym

__all__ = [
    "DEFAULT_MYCOBANK_URL",
    "PACKAGE_VERSION",
    "PycoBankError",
    "PycoBank",
    "MycoBank",
    "MycoBankRecord",
    "Synonym",
    "UnknownColumn",
    "build_database",
]
