import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_VERSION = 2


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialise(database_path: Path) -> None:
    connection = connect(database_path)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS buyer_profile_versions (
                version INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                profile TEXT NOT NULL
            )
            """
        )
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        connection.commit()
    finally:
        connection.close()


def save_buyer_profile(database_path: Path, profile: dict) -> dict:
    """Append a new immutable version; earlier versions are never touched."""
    connection = connect(database_path)
    try:
        created_at = datetime.now(UTC).isoformat()
        cursor = connection.execute(
            "INSERT INTO buyer_profile_versions (created_at, profile) VALUES (?, ?)",
            (created_at, json.dumps(profile)),
        )
        connection.commit()
        return {"version": cursor.lastrowid, "created_at": created_at, "profile": profile}
    finally:
        connection.close()


def latest_buyer_profile(database_path: Path) -> dict | None:
    connection = connect(database_path)
    try:
        row = connection.execute(
            "SELECT version, created_at, profile FROM buyer_profile_versions "
            "ORDER BY version DESC LIMIT 1"
        ).fetchone()
    finally:
        connection.close()
    return _version(row) if row else None


def buyer_profile_versions(database_path: Path) -> list[dict]:
    connection = connect(database_path)
    try:
        rows = connection.execute(
            "SELECT version, created_at, profile FROM buyer_profile_versions "
            "ORDER BY version DESC"
        ).fetchall()
    finally:
        connection.close()
    return [_version(row) for row in rows]


def _version(row: sqlite3.Row) -> dict:
    return {
        "version": row["version"],
        "created_at": row["created_at"],
        "profile": json.loads(row["profile"]),
    }
