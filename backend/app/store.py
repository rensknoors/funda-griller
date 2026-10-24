import dataclasses
import json
import sqlite3
from pathlib import Path

from app.ports import Listing

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    funda_id TEXT PRIMARY KEY,
    url TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS listing_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    funda_id TEXT NOT NULL REFERENCES listings(funda_id),
    fetched_at TEXT NOT NULL,
    data TEXT NOT NULL
);
"""


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialise(database_path: Path) -> None:
    connection = connect(database_path)
    try:
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        connection.executescript(_SCHEMA)
        connection.commit()
    finally:
        connection.close()


def add_snapshot(database_path: Path, listing: Listing, fetched_at: str, status: str) -> None:
    data = {**dataclasses.asdict(listing), "status": status}
    connection = connect(database_path)
    try:
        connection.execute(
            "INSERT OR IGNORE INTO listings (funda_id, url) VALUES (?, ?)",
            (listing.funda_id, listing.url),
        )
        connection.execute(
            "INSERT INTO listing_snapshots (funda_id, fetched_at, data) VALUES (?, ?, ?)",
            (listing.funda_id, fetched_at, json.dumps(data)),
        )
        connection.commit()
    finally:
        connection.close()


def get_listing(database_path: Path, funda_id: str) -> dict | None:
    connection = connect(database_path)
    try:
        return _read_listing(connection, funda_id)
    finally:
        connection.close()


def _read_listing(connection: sqlite3.Connection, funda_id: str) -> dict | None:
    row = connection.execute(
        "SELECT funda_id, url FROM listings WHERE funda_id = ?", (funda_id,)
    ).fetchone()
    if row is None:
        return None
    snapshots = connection.execute(
        "SELECT id, fetched_at, data FROM listing_snapshots WHERE funda_id = ? ORDER BY id DESC",
        (funda_id,),
    ).fetchall()
    return {
        "funda_id": row["funda_id"],
        "url": row["url"],
        "snapshots": [
            {"id": s["id"], "fetched_at": s["fetched_at"], **json.loads(s["data"])}
            for s in snapshots
        ],
    }


def list_listings(database_path: Path) -> list[dict]:
    connection = connect(database_path)
    try:
        ids = [
            row["funda_id"]
            for row in connection.execute("SELECT funda_id FROM listings ORDER BY rowid DESC")
        ]
        return [_read_listing(connection, funda_id) for funda_id in ids]
    finally:
        connection.close()
