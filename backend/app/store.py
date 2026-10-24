import dataclasses
import json
import re
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.ports import Listing, PricePoint

SCHEMA_VERSION = 4

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
CREATE TABLE IF NOT EXISTS source_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    funda_id TEXT NOT NULL REFERENCES listings(funda_id),
    source TEXT NOT NULL,
    attempted_at TEXT NOT NULL,
    outcome TEXT NOT NULL,
    reason TEXT,
    facts TEXT
);
CREATE TABLE IF NOT EXISTS verdicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    funda_id TEXT NOT NULL REFERENCES listings(funda_id),
    created_at TEXT NOT NULL,
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
        connection.executescript(_SCHEMA)
        connection.commit()
    finally:
        connection.close()


def add_snapshot(
    database_path: Path, listing: Listing, fetched_at: str, status: str, entry: str = "fetched"
) -> None:
    """`entry` records how the snapshot came in: fetched by the provider or entered manually."""
    data = {**dataclasses.asdict(listing), "status": status, "entry": entry}
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


def listing_from_snapshot(funda_id: str, url: str, snapshot: dict) -> Listing:
    """Rebuild the Listing a snapshot was taken from, for Source clients refetched on their own."""
    fields = {f.name for f in dataclasses.fields(Listing)}
    data = {key: value for key, value in snapshot.items() if key in fields}
    return Listing(
        **{
            **data,
            "funda_id": funda_id,
            "url": url,
            "price_history": tuple(PricePoint(**p) for p in snapshot.get("price_history", ())),
            "photo_urls": tuple(snapshot.get("photo_urls", ())),
        }
    )


def add_source_run(
    database_path: Path,
    funda_id: str,
    source: str,
    attempted_at: str,
    outcome: str,
    reason: str | None = None,
    facts: list[dict] | None = None,
) -> None:
    """Append one Source run. Earlier runs stay, so a failed refetch never erases good facts."""
    connection = connect(database_path)
    try:
        connection.execute(
            "INSERT INTO source_runs (funda_id, source, attempted_at, outcome, reason, facts) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                funda_id,
                source,
                attempted_at,
                outcome,
                reason,
                json.dumps(facts) if facts is not None else None,
            ),
        )
        connection.commit()
    finally:
        connection.close()


def source_runs(database_path: Path, funda_id: str) -> dict[str, dict]:
    """Per Source: its latest run, and its latest succeeded run (whose facts the Case shows)."""
    connection = connect(database_path)
    try:
        rows = connection.execute(
            "SELECT source, attempted_at, outcome, reason, facts FROM source_runs "
            "WHERE funda_id = ? ORDER BY id",
            (funda_id,),
        ).fetchall()
    finally:
        connection.close()
    runs: dict[str, dict] = {}
    for row in rows:
        run = {
            "attempted_at": row["attempted_at"],
            "outcome": row["outcome"],
            "reason": row["reason"],
            "facts": json.loads(row["facts"]) if row["facts"] is not None else None,
        }
        entry = runs.setdefault(row["source"], {"latest": run, "last_success": None})
        entry["latest"] = run
        if run["outcome"] == "succeeded":
            entry["last_success"] = run
    return runs


_PHOTO_NAME = re.compile(r"^[0-9a-f]{32}(\.[a-z0-9]{1,5})?$")
_PHOTO_SUFFIX = re.compile(r"\.[a-z0-9]{1,5}$")


def _photo_dir(media_dir: Path, funda_id: str) -> Path:
    return media_dir / "listings" / funda_id / "photos"


def save_photo(media_dir: Path, funda_id: str, filename: str, content: bytes) -> str:
    """Store an uploaded photo under a generated name; returns that name."""
    suffix = _PHOTO_SUFFIX.search(filename.lower())
    name = uuid.uuid4().hex + (suffix.group(0) if suffix else "")
    directory = _photo_dir(media_dir, funda_id)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_bytes(content)
    return name


def photo_path(media_dir: Path, funda_id: str, name: str) -> Path | None:
    if not funda_id.isdigit() or not _PHOTO_NAME.match(name):
        return None
    path = _photo_dir(media_dir, funda_id) / name
    return path if path.is_file() else None


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


def add_verdict(database_path: Path, funda_id: str, created_at: str, verdict: dict) -> dict:
    """Append a Verdict; earlier ones stay as its history. Returns it with id and per-Listing version."""
    connection = connect(database_path)
    try:
        cursor = connection.execute(
            "INSERT INTO verdicts (funda_id, created_at, data) VALUES (?, ?, ?)",
            (funda_id, created_at, json.dumps(verdict)),
        )
        connection.commit()
        row_id = cursor.lastrowid
    finally:
        connection.close()
    return next(v for v in verdicts(database_path, funda_id) if v["id"] == row_id)


def verdicts(database_path: Path, funda_id: str) -> list[dict]:
    """A Listing's Verdicts, newest first, each numbered from 1 in the order they were made."""
    connection = connect(database_path)
    try:
        rows = connection.execute(
            "SELECT id, created_at, data FROM verdicts WHERE funda_id = ? ORDER BY id",
            (funda_id,),
        ).fetchall()
    finally:
        connection.close()
    return [
        {"id": row["id"], "version": number, "created_at": row["created_at"], **json.loads(row["data"])}
        for number, row in enumerate(rows, start=1)
    ][::-1]


def listings_with_verdicts(database_path: Path) -> list[str]:
    connection = connect(database_path)
    try:
        return [
            row["funda_id"]
            for row in connection.execute("SELECT DISTINCT funda_id FROM verdicts ORDER BY funda_id")
        ]
    finally:
        connection.close()
