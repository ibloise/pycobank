"""Dataclasses returned by the PycoBank query client."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


SYNONYM_RE = re.compile(r"(?:^|\s-\s)(?P<name>.+?)\s+\[MB#(?P<mycobank>\d+)\]")


@dataclass(frozen=True)
class Synonym:
    """A parsed synonym mention from the MycoBank ``synonymy`` text."""

    name: str
    mycobank: str


@dataclass(frozen=True)
class MycoBankRecord:
    """A single row from the MycoBank MBList SQLite database."""

    data: dict[str, Any]
    score: float | None = None

    @property
    def id(self) -> str | None:
        return self._get("id")

    @property
    def taxon_name(self) -> str | None:
        return self._get("taxon_name")

    @property
    def rank(self) -> str | None:
        return self._get("rank")

    @property
    def mycobank(self) -> str | None:
        return self._get("mycobank")

    @property
    def current_mycobank(self) -> str | None:
        return self._get("current_mycobank")

    @property
    def current_name(self) -> str | None:
        return self._get("current_name")

    @property
    def classification(self) -> str | None:
        return self._get("classification")

    @property
    def taxonomy(self) -> tuple[str, ...]:
        value = self.classification or ""
        return tuple(part.strip() for part in value.split(",") if part.strip())

    @property
    def synonymy(self) -> str | None:
        return self._get("synonymy")

    @property
    def synonyms(self) -> tuple[Synonym, ...]:
        text = self.synonymy or ""
        matches = []
        for match in SYNONYM_RE.finditer(text):
            name = " ".join(match.group("name").split())
            if name.lower().startswith(("current name:", "basionym:")):
                continue
            matches.append(Synonym(name=name.lstrip("- "), mycobank=match.group("mycobank")))
        return tuple(matches)

    def summary(self) -> dict[str, Any]:
        """Return the fields most often needed for nomenclature queries."""
        return {
            "score": self.score,
            "id": self.id,
            "taxon_name": self.taxon_name,
            "rank": self.rank,
            "name_status": self._get("name_status"),
            "mycobank": self.mycobank,
            "current_mycobank": self.current_mycobank,
            "current_name": self.current_name,
            "taxonomy": self.taxonomy,
            "synonyms": [synonym.__dict__ for synonym in self.synonyms],
        }

    def _get(self, key: str) -> str | None:
        value = self.data.get(key)
        if value is None:
            return None
        return str(value)
