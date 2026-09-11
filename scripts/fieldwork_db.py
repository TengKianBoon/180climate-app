"""Create and verify SQLite backups for the Fieldwork pilot.

The command never selects a production path implicitly. Restore requires an
explicit destination and confirmation flag. Use only with an approved private
storage destination and the documented retention/deletion rules.
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def _schema_version(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"Database not found: {path}")
    with sqlite3.connect(path) as conn:
        row = conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()
    if not row:
        raise ValueError("Not a recognised Fieldwork database")
    return str(row[0])


def backup(source: Path, output: Path) -> None:
    _schema_version(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as src, sqlite3.connect(output) as dst:
        src.backup(dst)
    if _schema_version(output) != _schema_version(source):
        raise RuntimeError("Backup verification failed")


def restore(source: Path, destination: Path, confirmed: bool) -> None:
    if not confirmed:
        raise ValueError("Restore requires --confirm-replace")
    _schema_version(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)
    if _schema_version(destination) != _schema_version(source):
        raise RuntimeError("Restore verification failed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup or restore the Fieldwork SQLite database")
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
