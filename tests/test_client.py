from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from pycobank import PycoBank, MycoBank


class MycoBankClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "mycobank.sqlite3"
        self._make_db(self.db_path)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_search_prefix_returns_summary_fields(self) -> None:
        db = MycoBank(self.db_path)
        rows = db.search("Agaricus", match="prefix")
        self.assertEqual(rows[0].mycobank, "17030")
        self.assertEqual(rows[0].rank, "gen.")
        self.assertIn("Agaricales", rows[0].taxonomy)

    def test_search_normalizes_excel_whitespace(self) -> None:
        db = MycoBank(self.db_path)
        rows = db.search("  Amanita\xa0  muscaria  ", match="exact")
        self.assertEqual(rows[0].taxon_name, "Amanita muscaria")

    def test_fuzzy_search_scores_close_names(self) -> None:
        db = MycoBank(self.db_path)
        rows = db.fuzzy_search("Amanita muscarria", threshold=0.6)
        self.assertEqual(rows[0].taxon_name, "Amanita muscaria")
        self.assertGreater(rows[0].score, 0.9)

    def test_get_and_synonyms(self) -> None:
        db = MycoBank(self.db_path)
        record = db.get("17030")
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record.current_name, "Agaricus")
        self.assertEqual(record.synonyms[0].mycobank, "17621")

    def test_high_level_class_helpers_for_custom_scripts(self) -> None:
        db = PycoBank(self.db_path)
        self.assertEqual(db.search_names("Agaricus")[0].mycobank, "17030")
        self.assertEqual(db.search_current_names("Amanita")[0].taxon_name, "Amanita muscaria")
        self.assertEqual(db.search_synonyms("Fungus Tourn.")[0].taxon_name, "Agaricus")
        self.assertEqual(db.nearest_names("Amanita muscarria")[0].taxon_name, "Amanita muscaria")

    @staticmethod
    def _make_db(path: Path) -> None:
        conn = sqlite3.connect(path)
        columns = [
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
        ]
        conn.execute(
            "CREATE TABLE mycobank ("
            + ", ".join(f"{column} TEXT" for column in columns)
            + ")"
        )
        conn.execute(
            "CREATE TABLE _mycobank_columns (position INTEGER PRIMARY KEY, column_name TEXT, original_header TEXT)"
        )
        conn.execute(
            "CREATE TABLE _mycobank_import_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.executemany(
            "INSERT INTO _mycobank_columns VALUES (?, ?, ?)",
            [(idx + 1, column, column) for idx, column in enumerate(columns)],
        )
        conn.execute(
            "INSERT INTO _mycobank_import_meta VALUES ('row_count', '2')"
        )
        conn.executemany(
            "INSERT INTO mycobank VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    "1",
                    "Agaricus",
                    "L.",
                    "L.",
                    "gen.",
                    "1753",
                    "Legitimate",
                    "17030",
                    "",
                    "Fungi, Basidiomycota, Agaricales, Agaricaceae",
                    "17030",
                    "Agaricus",
                    "Current name: Agaricus L. [MB#17030] Taxonomic synonyms: - Fungus Tourn. [MB#17621]",
                ),
                (
                    "2",
                    "Amanita muscaria",
                    "",
                    "",
                    "sp.",
                    "1783",
                    "Legitimate",
                    "12345",
                    "",
                    "Fungi, Basidiomycota, Agaricales, Amanitaceae, Amanita",
                    "12345",
                    "Amanita muscaria",
                    "Current name: Amanita muscaria [MB#12345]",
                ),
            ],
        )
        conn.commit()
        conn.close()


if __name__ == "__main__":
    unittest.main()
