"""Command line interface for PycoBank."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .builder import build_database
from .client import MycoBank
from .contracts import DEFAULT_MYCOBANK_URL, DEFAULT_SHEET, DEFAULT_TABLE


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pycobank",
        description="Construye y consulta una base SQLite local de MycoBank.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="Descargar/importar MBList a SQLite")
    build.add_argument("--db", type=Path, required=True, help="Ruta del SQLite de salida")
    build.add_argument("--zip", dest="zip_path", type=Path, help="ZIP local descargado manualmente")
    build.add_argument("--url", default=DEFAULT_MYCOBANK_URL, help="URL del ZIP remoto")
    build.add_argument("--cache-dir", type=Path, help="Directorio de caché para descarga")
    build.add_argument("--table", default=DEFAULT_TABLE, help="Tabla principal")
    build.add_argument("--sheet", default=DEFAULT_SHEET, help="Hoja Excel a importar")
    build.add_argument("--no-replace", action="store_false", dest="replace")
    build.add_argument("--refresh", action="store_true", help="Forzar descarga nueva")
    build.add_argument("--batch-size", type=int, default=10_000)
    build.add_argument("--index-column", action="append", default=[])
    build.set_defaults(replace=True)

    search = subparsers.add_parser("search", help="Buscar nombres o patrones")
    add_db_arg(search)
    search.add_argument("text", help="Texto a buscar")
    search.add_argument("--mode", choices=("contains", "prefix", "exact", "fuzzy", "regex"), default="contains")
    search.add_argument("--field", action="append", dest="fields", help="Campo a buscar; puede repetirse")
    search.add_argument("--rank", help="Filtrar por rank")
    search.add_argument("--current-only", action="store_true", help="Solo nombres actuales")
    search.add_argument("--limit", type=int, default=25)
    search.add_argument("--threshold", type=float, default=0.55, help="Umbral para modo fuzzy")
    search.add_argument("--json", action="store_true", help="Salida JSON")

    show = subparsers.add_parser("show", help="Mostrar una fila por id o número MycoBank")
    add_db_arg(show)
    show.add_argument("identifier")
    show.add_argument("--json", action="store_true")

    columns = subparsers.add_parser("columns", help="Listar columnas importadas")
    add_db_arg(columns)

    meta = subparsers.add_parser("meta", help="Mostrar metadatos de importación")
    add_db_arg(meta)

    return parser


def add_db_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", type=Path, required=True, help="Ruta de la SQLite MycoBank")
    parser.add_argument("--table", default=DEFAULT_TABLE, help="Tabla principal")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "build":
        build_database(
            db_path=args.db,
            zip_path=args.zip_path,
            url=args.url,
            cache_dir=args.cache_dir,
            table_name=args.table,
            sheet_name=args.sheet,
            replace=args.replace,
            refresh=args.refresh,
            batch_size=args.batch_size,
            index_columns=args.index_column,
        )
        return 0

    db = MycoBank(args.db, table_name=args.table)
    if args.command == "search":
        if args.fields:
            fields = tuple(args.fields)
        elif args.mode == "fuzzy":
            fields = ("taxon_name", "current_name")
        else:
            fields = ("taxon_name",)
        if args.mode == "fuzzy":
            rows = db.fuzzy_search(
                args.text,
                fields=fields,
                limit=args.limit,
                threshold=args.threshold,
                rank=args.rank,
                current_only=args.current_only,
            )
        elif args.mode == "regex":
            rows = db.regex_search(
                args.text,
                fields=fields,
                limit=args.limit,
                rank=args.rank,
                current_only=args.current_only,
            )
        else:
            rows = db.search(
                args.text,
                fields=fields,
                limit=args.limit,
                match=args.mode,
                rank=args.rank,
                current_only=args.current_only,
            )
        payload = [row.summary() for row in rows]
        print_json(payload) if args.json else print_table(payload)
        return 0

    if args.command == "show":
        row = db.get(args.identifier)
        payload = None if row is None else row.summary() | {"raw": row.data}
        if args.json:
            print_json(payload)
        elif row is None:
            print("No encontrado")
        else:
            print_json(payload)
        return 0

    if args.command == "columns":
        print_json(db.columns())
        return 0

    if args.command == "meta":
        print_json(db.metadata())
        return 0

    parser.error(f"Comando no soportado: {args.command}")
    return 2


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def print_table(rows: list[dict[str, object]]) -> None:
    for row in rows:
        score = "" if row.get("score") is None else f" score={row['score']}"
        print(
            f"{row.get('mycobank') or '-'} | {row.get('taxon_name') or '-'} "
            f"| rank={row.get('rank') or '-'} | current={row.get('current_name') or '-'}{score}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
