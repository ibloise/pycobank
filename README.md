# PycoBank

PycoBank builds a local SQLite database from the public MycoBank `MBList.zip`
export and provides a small Python API and CLI for nomenclatural searches.

The builder can use either the official ZIP URL or a ZIP downloaded manually.
The query layer focuses on practical access to `rank`, MycoBank identifiers,
current names, taxonomy and synonyms, while still exposing raw row data when
needed.

## Installation

```bash
cd PycoBank
python -m pip install -e .
```

## Build a database

Download from MycoBank:

```bash
pycobank build --db data/mycobank.sqlite3
```

Use a manually downloaded ZIP:

```bash
pycobank build --zip ../MBList.zip --db data/mycobank.sqlite3
```

The default source URL is:

```text
https://www.mycobank.org/images/MBList.zip
```

## Use from custom Python scripts

```python
from pycobank import PycoBank

db = PycoBank("../data/mycobank.sqlite3")

for record in db.search_names("Agaricus", limit=5, match="prefix"):
    print(record.mycobank, record.taxon_name, record.rank, record.current_name)
    print(record.taxonomy)

near = db.nearest_names("Amanita muscarria", limit=5, threshold=0.60)
print(near[0].summary())

current = db.search_current_names("Agaricus", match="prefix")
synonyms = db.search_synonyms("Fungus Tourn.")

record = db.get("17030")
print(record.current_name)
print(record.synonyms)
```

The class can also build the database before opening it:

```python
from pycobank import PycoBank

# From a manually downloaded ZIP.
db = PycoBank.from_zip("../MBList.zip", "data/mycobank.sqlite3")

# Or directly from the default MycoBank URL.
db = PycoBank.from_url("data/mycobank.sqlite3", refresh=False)
```

For advanced queries, the lower-level methods remain available:

```python
rows = db.search(
    "Agaricus",
    fields=("taxon_name", "current_name", "synonymy"),
    match="contains",
    rank="sp.",
    limit=20,
)

patterns = db.search_pattern(r"^Agaricus .*musc", fields=("taxon_name",))
raw_rows = db.query("SELECT rank, COUNT(*) AS n FROM mycobank GROUP BY rank")
```

## Query from the CLI

```bash
pycobank search --db ../data/mycobank.sqlite3 Agaricus --mode prefix --limit 5
pycobank search --db ../data/mycobank.sqlite3 "Amanita muscarria" --mode fuzzy --json
pycobank search --db ../data/mycobank.sqlite3 "^Agaricus .*" --mode regex --field taxon_name
pycobank search --db ../data/mycobank.sqlite3 "Taxonomic synonyms" --field synonymy
pycobank show --db ../data/mycobank.sqlite3 17030 --json
pycobank columns --db ../data/mycobank.sqlite3
pycobank meta --db ../data/mycobank.sqlite3
```

## Public API

- `build_database(...)`: downloads or imports `MBList.zip` and writes SQLite.
- `PycoBank(...)`: main class for custom scripts using an existing SQLite DB.
- `PycoBank.from_zip(...)`: build from a manually downloaded ZIP and open it.
- `PycoBank.from_url(...)`: download from URL, build and open the database.
- `PycoBank.search_names(...)`: search the original taxon-name field.
- `PycoBank.search_current_names(...)`: search accepted/current names.
- `PycoBank.search_synonyms(...)`: search the free-text synonymy field.
- `PycoBank.nearest_names(...)`: proximity search across taxon and current
  names.
- `PycoBank.search_pattern(...)`: regular expression search.
- `MycoBank.search(...)`: exact, prefix or contains searches with optional rank
  and current-name filters.
- `MycoBank.fuzzy_search(...)`: proximity search over selected fields.
- `MycoBank.regex_search(...)`: Python regular expression search.
- `MycoBank.get(...)`: fetch by internal id, MycoBank number or current
  MycoBank number.
- `MycoBankRecord.summary()`: compact view with rank, id, current name,
  taxonomy and parsed synonyms.

## MycoBank Data Use Disclaimer

PycoBank is a client and local indexing tool. It does not own, curate, or
redistribute the MycoBank data. When you download or import `MBList.zip`, the
resulting SQLite database is a local transformation of data provided by
MycoBank, and your use of that data remains subject to the current terms,
conditions, citation requirements, and access policies published by MycoBank:

- MycoBank website: <https://www.mycobank.org/>
- Default MBList export used by this package:
  <https://www.mycobank.org/images/MBList.zip>

Before using the data in publications, services, redistributed datasets,
commercial workflows, or automated pipelines, review the official MycoBank
conditions and cite MycoBank as required by those conditions. Do not imply that
PycoBank is endorsed by, affiliated with, or maintained by MycoBank. Avoid
abusive download patterns; cache the ZIP locally when rebuilding databases and
respect any rate limits, access restrictions, or redistribution limits stated by
MycoBank.

The `PycoBank` code may be licensed independently from the MycoBank data. A
local SQLite database produced by this tool may therefore have different legal
and attribution obligations from this software package itself.

## Responsible Use

PycoBank is independent software and is not affiliated with, endorsed by, or
maintained by MycoBank. Database exports and their formats may change. Validate
results before scientific, clinical or production use.

## Tests

```bash
python -m unittest discover -s tests -v
```
