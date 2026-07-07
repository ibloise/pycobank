from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from openpyxl import Workbook

from pycobank.builder import build_database
from pycobank.client import MycoBank


class BuildDatabaseTests(unittest.TestCase):
    def test_build_database_from_local_zip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workbook_path = tmp_path / "MBList.xlsx"
            zip_path = tmp_path / "MBList.zip"
            db_path = tmp_path / "mycobank.sqlite3"

            wb = Workbook()
            ws = wb.active
            ws.title = "Sheet1"
            ws.append(
                [
                    "ID",
                    "Taxon name",
                    "Authors",
                    "Authors (abbreviated)",
                    "Rank",
                    "Year of effective publication",
                    "Name status",
                    "MycoBank #",
                    "Hyperlink to MB",
                    "Classification",
                    "Current MycoBank #",
                    "Current name",
                    "Synonymy",
                ]
            )
            ws.append(
                [
                    "1",
                    "Agaricus",
                    "Linnaeus",
                    "L.",
                    "gen.",
                    "1753",
                    "Legitimate",
                    "17030",
                    "",
                    "Fungi, Basidiomycota, Agaricales",
                    "17030",
                    "Agaricus",
                    "Current name: Agaricus L. [MB#17030]",
                ]
            )
            wb.save(workbook_path)

            with ZipFile(zip_path, "w") as zf:
                zf.write(workbook_path, arcname="MBList.xlsx")

            build_database(db_path=db_path, zip_path=zip_path)

            db = MycoBank(db_path)
            self.assertEqual(db.metadata()["row_count"], "1")
            self.assertEqual(db.get("17030").taxon_name, "Agaricus")  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()
