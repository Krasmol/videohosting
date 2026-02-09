"""Minimal SQLite schema migration helper.

This project historically shipped a pre-created SQLite DB. When we add new columns
or tables, SQLAlchemy's `create_all()` will create missing tables but will NOT add
missing columns to existing tables. That can break auth/login immediately.

For this demo app we keep a small, safe, idempotent migration for SQLite only.
"""

from __future__ import annotations

from sqlalchemy import text

from app import db


def _table_columns(table_name: str) -> set[str]:
    rows = db.session.execute(text(f"PRAGMA table_info({table_name})")).mappings().all()
    return {r["name"] for r in rows}


def _table_exists(table_name: str) -> bool:
    row = db.session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
        {"t": table_name},
    ).first()
    return row is not None


def _add_column(table: str, ddl: str) -> None:
    # ddl should be like: "ADD COLUMN is_moderator INTEGER NOT NULL DEFAULT 0"
    db.session.execute(text(f"ALTER TABLE {table} {ddl}"))


def ensure_sqlite_schema(app) -> None:
    """Bring an older SQLite DB up to date enough for the app to run."""

    uri = str(app.config.get("SQLALCHEMY_DATABASE_URI", ""))
    if not uri.startswith("sqlite:"):
        return

    # Create missing tables first.
    db.create_all()

    # USERS: add moderator role flag.
    if _table_exists("users"):
        cols = _table_columns("users")
        if "is_moderator" not in cols:
            # SQLite doesn't have a real BOOLEAN; INTEGER 0/1 is standard.
            _add_column("users", "ADD COLUMN is_moderator INTEGER NOT NULL DEFAULT 0")

    # VIDEOS: add all_categories flag and thumbnail_path if missing.
    if _table_exists("videos"):
        cols = _table_columns("videos")
        if "all_categories" not in cols:
            _add_column("videos", "ADD COLUMN all_categories INTEGER NOT NULL DEFAULT 0")
        if "thumbnail_path" not in cols:
            _add_column("videos", "ADD COLUMN thumbnail_path VARCHAR(500)")

    db.session.commit()
