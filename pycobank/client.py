"""SQLite query client for local MycoBank MBList databases."""

from __future__ import annotations

import difflib
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from .builder import build_database, quote_ident
from .contracts import DEFAULT_MYCOBANK_URL, DEFAULT_TABLE, SUMMARY_COLUMNS
from .models import MycoBankRecord


class PycoBankError(Exception):
    """Base exception for PycoBank client errors."""


class UnknownColumn(PycoBankError, ValueError):
    """Raised when a query references a column absent from the SQLite DB."""


@dataclass(frozen=True)
class SearchOptions:
    """Options for name and pattern searches."""

    fields: tuple[str, ...] = ("taxon_name",)
    limit: int = 25
    threshold: float = 0.0
    include_raw: bool = False


class MycoBank:
    """Convenient access layer for a local MycoBank SQLite export."""

    def __init__(self, db_path: str | Path, *, table_name: str = DEFAULT_TABLE) -> None:
        self.db_path = Path(db_path)
        self.table_name = table_name
        if not self.db_path.exists():
            raise FileNotFoundError(f"No existe la base de datos: {self.db_path}")

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def columns(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT position, column_name, original_header
                FROM _mycobank_columns
                ORDER BY position
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def column_names(self) -> set[str]:
        return {row["column_name"] for row in self.columns()}

    def metadata(self) -> dict[str, str]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT key, value FROM _mycobank_import_meta ORDER BY key"
            ).fetchall()
        return {row["key"]: row["value"] for row in rows}

    def query(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def get(self, identifier: str | int) -> MycoBankRecord | None:
        """Find a row by internal ``id`` or MycoBank number."""
        sql = (
            f"SELECT * FROM {quote_ident(self.table_name)} "
            "WHERE id = ? OR mycobank = ? OR current_mycobank = ? LIMIT 1"
        )
        with self.connect() as conn:
            row = conn.execute(sql, (str(identifier), str(identifier), str(identifier))).fetchone()
        return None if row is None else MycoBankRecord(dict(row))

    def search(
        self,
        text: str,
        *,
        fields: Iterable[str] = ("taxon_name",),
        limit: int = 25,
        match: str = "contains",
        rank: str | None = None,
        current_only: bool = False,
    ) -> list[MycoBankRecord]:
        """Search text using SQLite ``LIKE`` over one or more columns."""
        selected_fields = tuple(fields)
        self._validate_columns(selected_fields)
        where, params = self._text_where(text, selected_fields, match)
        where, params = self._add_filters(where, params, rank=rank, current_only=current_only)
        return self._select_records(where, params, limit=limit)

    def fuzzy_search(
        self,
        text: str,
        *,
        fields: Iterable[str] = ("taxon_name",),
        limit: int = 25,
        candidate_limit: int = 500,
        threshold: float = 0.55,
        rank: str | None = None,
        current_only: bool = False,
    ) -> list[MycoBankRecord]:
        """Search names by proximity using a bounded SQLite candidate set."""
        selected_fields = tuple(fields)
        self._validate_columns(selected_fields)
        tokens = self._tokens(text)
        candidate_where_parts = []
        params: list[Any] = []
        for token in tokens:
            part, part_params = self._text_where(token, selected_fields, "contains")
            candidate_where_parts.append(f"({part})")
            params.extend(part_params)
        where = " OR ".join(candidate_where_parts) if candidate_where_parts else "1 = 1"
        where, params = self._add_filters(where, params, rank=rank, current_only=current_only)

        candidates = self._select_records(where, params, limit=candidate_limit)
        query_norm = self._normalize(text)
        scored: list[MycoBankRecord] = []
        for record in candidates:
            best = max(
                (
                    difflib.SequenceMatcher(
                        None,
                        query_norm,
                        self._normalize(record.data.get(field) or ""),
                    ).ratio()
                    for field in selected_fields
                ),
                default=0.0,
            )
            if best >= threshold:
                scored.append(MycoBankRecord(record.data, score=round(best, 4)))

        scored.sort(
            key=lambda record: (
                record.score or 0.0,
                self._normalize(record.taxon_name or "") == query_norm,
            ),
            reverse=True,
        )
        return scored[:limit]

    def regex_search(
        self,
        pattern: str,
        *,
        fields: Iterable[str] = ("taxon_name", "current_name"),
        limit: int = 25,
        rank: str | None = None,
        current_only: bool = False,
        flags: int = re.IGNORECASE,
    ) -> list[MycoBankRecord]:
        """Search rows with a Python regular expression over selected fields."""
        selected_fields = tuple(fields)
        self._validate_columns(selected_fields)
        regex = re.compile(pattern, flags)
        where, params = self._add_filters("1 = 1", [], rank=rank, current_only=current_only)
        selected = SUMMARY_COLUMNS
        self._validate_columns(selected)
        sql = (
            "SELECT "
            + ", ".join(quote_ident(column) for column in selected)
            + f" FROM {quote_ident(self.table_name)} WHERE {where}"
        )
        matches: list[MycoBankRecord] = []
        with self.connect() as conn:
            for row in conn.execute(sql, params):
                record = MycoBankRecord(dict(row))
                if any(regex.search(str(record.data.get(field) or "")) for field in selected_fields):
                    matches.append(record)
                if len(matches) >= limit:
                    break
        return matches

    def taxonomy(self, identifier: str | int) -> tuple[str, ...]:
        record = self.get(identifier)
        return () if record is None else record.taxonomy

    def synonyms(self, identifier: str | int):
        record = self.get(identifier)
        return () if record is None else record.synonyms

    def _validate_columns(self, columns: Iterable[str]) -> None:
        available = self.column_names()
        missing = [column for column in columns if column not in available]
        if missing:
            raise UnknownColumn(
                "Columnas no válidas: "
                + ", ".join(missing)
                + ". Columnas disponibles: "
                + ", ".join(sorted(available))
            )

    def _select_records(
        self,
        where: str,
        params: Sequence[Any],
        *,
        limit: int,
        columns: Sequence[str] | None = None,
    ) -> list[MycoBankRecord]:
        selected = columns or SUMMARY_COLUMNS
        self._validate_columns(selected)
        sql = (
            "SELECT "
            + ", ".join(quote_ident(column) for column in selected)
            + f" FROM {quote_ident(self.table_name)} WHERE {where} LIMIT ?"
        )
        with self.connect() as conn:
            rows = conn.execute(sql, (*params, int(limit))).fetchall()
        return [MycoBankRecord(dict(row)) for row in rows]

    def _text_where(
        self,
        text: str,
        fields: Sequence[str],
        match: str,
    ) -> tuple[str, list[Any]]:
        text = self._clean_search_text(text)
        if match == "exact":
            value = text
        elif match == "prefix":
            value = f"{text}%"
        elif match == "contains":
            value = f"%{text}%"
        else:
            raise ValueError("match debe ser 'exact', 'prefix' o 'contains'")
        parts = [f"{quote_ident(field)} LIKE ? COLLATE NOCASE" for field in fields]
        return " OR ".join(parts), [value] * len(fields)

    def _add_filters(
        self,
        where: str,
        params: list[Any],
        *,
        rank: str | None,
        current_only: bool,
    ) -> tuple[str, list[Any]]:
        filters = [f"({where})"]
        if rank is not None:
            self._validate_columns(("rank",))
            filters.append("rank = ?")
            params.append(rank)
        if current_only:
            self._validate_columns(("mycobank", "current_mycobank"))
            filters.append("mycobank = current_mycobank")
        return " AND ".join(filters), params

    @staticmethod
    def _normalize(value: str) -> str:
        value = MycoBank._clean_search_text(value).casefold()
        value = re.sub(r"\s+", " ", value)
        return value

    @staticmethod
    def _clean_search_text(value: object) -> str:
        """Normalize user/Excel input before building text queries."""
        text = "" if value is None else str(value)
        text = text.replace("\xa0", " ")
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def _tokens(cls, value: str) -> tuple[str, ...]:
        tokens = [
            token
            for token in re.split(r"\W+", cls._normalize(value))
            if len(token) >= 3
        ]
        return tuple(tokens) or (value,)


class PycoBank(MycoBank):
    """High-level class intended for direct use in custom Python scripts.

    ``PycoBank`` keeps the lower-level methods inherited from ``MycoBank`` and
    adds domain-specific helpers with stable defaults for common workflows.
    """

    @classmethod
    def from_zip(
        cls,
        zip_path: str | Path,
        db_path: str | Path,
        *,
        replace: bool = True,
        table_name: str = DEFAULT_TABLE,
    ) -> "PycoBank":
        """Build a SQLite database from a manually downloaded ZIP and open it."""
        build_database(
            db_path=Path(db_path),
            zip_path=Path(zip_path),
            replace=replace,
            table_name=table_name,
        )
        return cls(db_path, table_name=table_name)

    @classmethod
    def from_url(
        cls,
        db_path: str | Path,
        *,
        url: str = DEFAULT_MYCOBANK_URL,
        cache_dir: str | Path | None = None,
        refresh: bool = False,
        replace: bool = True,
        table_name: str = DEFAULT_TABLE,
    ) -> "PycoBank":
        """Download the MBList ZIP, build a SQLite database and open it."""
        build_database(
            db_path=Path(db_path),
            url=url,
            cache_dir=None if cache_dir is None else Path(cache_dir),
            refresh=refresh,
            replace=replace,
            table_name=table_name,
        )
        return cls(db_path, table_name=table_name)

    def search_names(
        self,
        text: str,
        *,
        limit: int = 25,
        match: str = "contains",
        rank: str | None = None,
        current_only: bool = False,
    ) -> list[MycoBankRecord]:
        """Search the original MycoBank taxon-name field."""
        return self.search(
            text,
            fields=("taxon_name",),
            limit=limit,
            match=match,
            rank=rank,
            current_only=current_only,
        )

    def search_current_names(
        self,
        text: str,
        *,
        limit: int = 25,
        match: str = "contains",
        rank: str | None = None,
    ) -> list[MycoBankRecord]:
        """Search the accepted/current name field."""
        return self.search(
            text,
            fields=("current_name",),
            limit=limit,
            match=match,
            rank=rank,
        )

    def search_synonyms(
        self,
        text: str,
        *,
        limit: int = 25,
        match: str = "contains",
        rank: str | None = None,
    ) -> list[MycoBankRecord]:
        """Search the free-text synonymy field."""
        return self.search(
            text,
            fields=("synonymy",),
            limit=limit,
            match=match,
            rank=rank,
        )

    def nearest_names(
        self,
        text: str,
        *,
        limit: int = 25,
        threshold: float = 0.55,
        rank: str | None = None,
        current_only: bool = False,
    ) -> list[MycoBankRecord]:
        """Find names close to ``text`` using taxon and current-name fields."""
        return self.fuzzy_search(
            text,
            fields=("taxon_name", "current_name"),
            limit=limit,
            threshold=threshold,
            rank=rank,
            current_only=current_only,
        )

    def search_pattern(
        self,
        pattern: str,
        *,
        fields: Iterable[str] = ("taxon_name", "current_name", "synonymy"),
        limit: int = 25,
        rank: str | None = None,
        current_only: bool = False,
        flags: int = re.IGNORECASE,
    ) -> list[MycoBankRecord]:
        """Search with a Python regular expression over selected fields."""
        return self.regex_search(
            pattern,
            fields=fields,
            limit=limit,
            rank=rank,
            current_only=current_only,
            flags=flags,
        )
