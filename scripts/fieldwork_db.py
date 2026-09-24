"""Create and verify SQLite backups for the unified 180Climate intake database.

The command never selects a production path implicitly. Restore requires an
explicit destination and confirmation flag. Use only with an approved private
storage destination and the documented retention/deletion rules.
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def _schema_versions(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise ValueError(f"Database not found: {path}")
    with sqlite3.connect(path) as conn:
        tables = {
            str(row[0])
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        versions: dict[str, str] = {}
        if "schema_meta" in tables:
            row = conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()
            if row:
                versions["fieldwork"] = str(row[0])
        if "intake_schema_meta" in tables:
            row = conn.execute(
                "SELECT value FROM intake_schema_meta WHERE key='schema_version'"
            ).fetchone()
            if row:
                versions["intake"] = str(row[0])
    if not versions:
        raise ValueError("Not a recognised 180Climate intake database")
    return versions


def backup(source: Path, output: Path) -> None:
    source_versions = _schema_versions(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as src, sqlite3.connect(output) as dst:
        src.backup(dst)
    if _schema_versions(output) != source_versions:
        raise RuntimeError("Backup verification failed")


def restore(source: Path, destination: Path, confirmed: bool) -> None:
    if not confirmed:
        raise ValueError("Restore requires --confirm-replace")
    source_versions = _schema_versions(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)
    if _schema_versions(destination) != source_versions:
        raise RuntimeError("Restore verification failed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup or restore the 180Climate intake SQLite database")
    sub = parser.add_subparsers(dest="command", required=True)
    backup_parser = sub.add_parser("backup")
    backup_parser.add_argument("--db", type=Path, required=True)
    backup_parser.add_argument("--output", type=Path, required=True)
    restore_parser = sub.add_parser("restore")
    restore_parser.add_argument("--backup", type=Path, required=True)
    restore_parser.add_argument("--db", type=Path, required=True)
    restore_parser.add_argument("--confirm-replace", action="store_true")
    args = parser.parse_args()
    if args.command == "backup":
        backup(args.db.resolve(), args.output.resolve())
    else:
        restore(args.backup.resolve(), args.db.resolve(), args.confirm_replace)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
