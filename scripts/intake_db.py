"""Canonical entry point for unified 180Climate intake backup and restore."""

from fieldwork_db import backup, main, restore

__all__ = ["backup", "restore", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
