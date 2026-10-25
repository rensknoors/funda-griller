import dataclasses
import json
import re
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.ports import Listing, PricePoint

SCHEMA_VERSION = 8

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
CREATE TABLE IF NOT EXISTS observation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    funda_id TEXT NOT NULL REFERENCES listings(funda_id),
    photo_set TEXT NOT NULL,
    attempted_at TEXT NOT NULL,
    outcome TEXT NOT NULL,
    reason TEXT,
    model TEXT,
    observations TEXT
);
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    funda_id TEXT NOT NULL REFERENCES listings(funda_id),
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    source_url TEXT,
    stored_name TEXT,
    sha256 TEXT,
    added_at TEXT NOT NULL,
    status TEXT NOT NULL,
    reason TEXT,
    page_count INTEGER,
    findings TEXT,
    rejected_findings INTEGER NOT NULL DEFAULT 0,
    model TEXT,
    extracted_at TEXT
);
CREATE TABLE IF NOT EXISTS listing_archive_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    funda_id TEXT NOT NULL REFERENCES listings(funda_id),
    archived INTEGER NOT NULL,
    at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS geocodes (
    address TEXT PRIMARY KEY,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL
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
        # Documents the user added were once of kind "upload" (a term GLOSSARY.md avoids).
        connection.execute("UPDATE documents SET kind = 'user' WHERE kind = 'upload'")
        connection.commit()
    finally:
        connection.close()


def add_snapshot(
    database_path: Path,
    listing: Listing,
    fetched_at: str,
    status: str,
    entry: str = "fetched",
    photos: list[dict] | None = None,
) -> None:
    """`entry` records how the snapshot came in: fetched by the provider or entered manually.
    `photos` are the snapshot's photos as kept on disk."""
    data = {**dataclasses.asdict(listing), "status": status, "entry": entry, "photos": photos or []}
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


def add_observation_run(
    database_path: Path,
    funda_id: str,
    photo_set: str,
    attempted_at: str,
    outcome: str,
    model: str | None,
    reason: str | None = None,
    observations: list[dict] | None = None,
) -> None:
    """Append one vision-model run over a photo set. A failed run never erases earlier Observations."""
    connection = connect(database_path)
    try:
        connection.execute(
            "INSERT INTO observation_runs "
            "(funda_id, photo_set, attempted_at, outcome, reason, model, observations) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                funda_id,
                photo_set,
                attempted_at,
                outcome,
                reason,
                model,
                json.dumps(observations) if observations is not None else None,
            ),
        )
        connection.commit()
    finally:
        connection.close()


def observation_runs(database_path: Path, funda_id: str, photo_set: str) -> dict:
    """For one photo set: its latest run, and its latest succeeded run (whose Observations count)."""
    connection = connect(database_path)
    try:
        rows = connection.execute(
            "SELECT id, attempted_at, outcome, reason, model, observations FROM observation_runs "
            "WHERE funda_id = ? AND photo_set = ? ORDER BY id",
            (funda_id, photo_set),
        ).fetchall()
    finally:
        connection.close()
    runs: dict = {"latest": None, "last_success": None}
    for row in rows:
        run = {
            "id": row["id"],
            "attempted_at": row["attempted_at"],
            "outcome": row["outcome"],
            "reason": row["reason"],
            "model": row["model"],
            "observations": json.loads(row["observations"]) if row["observations"] else [],
        }
        runs["latest"] = run
        if run["outcome"] == "succeeded":
            runs["last_success"] = run
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
    archive = connection.execute(
        "SELECT archived FROM listing_archive_events WHERE funda_id = ? ORDER BY id DESC LIMIT 1",
        (funda_id,),
    ).fetchone()
    return {
        "funda_id": row["funda_id"],
        "url": row["url"],
        "archived": bool(archive["archived"]) if archive else False,
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


def set_archived(database_path: Path, funda_id: str, archived: bool, at: str) -> None:
    """Archive or restore a Listing. Appends an event; snapshots and Source runs stay untouched."""
    connection = connect(database_path)
    try:
        connection.execute(
            "INSERT INTO listing_archive_events (funda_id, archived, at) VALUES (?, ?, ?)",
            (funda_id, int(archived), at),
        )
        connection.commit()
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


_DOCUMENT_NAME = re.compile(r"^[0-9a-f]{32}\.pdf$")
_DOCUMENT_FIELDS = (
    "name",
    "source_url",
    "stored_name",
    "sha256",
    "status",
    "reason",
    "page_count",
    "findings",
    "rejected_findings",
    "model",
    "extracted_at",
)


def _document_dir(media_dir: Path, funda_id: str) -> Path:
    return media_dir / "listings" / funda_id / "documents"


def save_document_file(media_dir: Path, funda_id: str, content: bytes) -> str:
    """Store a Document's bytes under a generated name; returns that name."""
    name = uuid.uuid4().hex + ".pdf"
    directory = _document_dir(media_dir, funda_id)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_bytes(content)
    return name


def document_file_path(media_dir: Path, funda_id: str, stored_name: str | None) -> Path | None:
    if not funda_id.isdigit() or not stored_name or not _DOCUMENT_NAME.match(stored_name):
        return None
    path = _document_dir(media_dir, funda_id) / stored_name
    return path if path.is_file() else None


def delete_document_file(media_dir: Path, funda_id: str, stored_name: str | None) -> None:
    path = document_file_path(media_dir, funda_id, stored_name)
    if path is not None:
        path.unlink()


def add_document(database_path: Path, funda_id: str, kind: str, name: str, added_at: str) -> int:
    """A new Document row, `pending` until it has been read and analysed."""
    connection = connect(database_path)
    try:
        cursor = connection.execute(
            "INSERT INTO documents (funda_id, kind, name, added_at, status) VALUES (?, ?, ?, ?, 'pending')",
            (funda_id, kind, name, added_at),
        )
        connection.commit()
        return cursor.lastrowid
    finally:
        connection.close()


def update_document(database_path: Path, document_id: int, **fields: object) -> None:
    unknown = set(fields) - set(_DOCUMENT_FIELDS)
    if unknown:
        raise ValueError(f"unknown Document fields: {sorted(unknown)}")
    if "findings" in fields:
        fields["findings"] = json.dumps(fields["findings"] or [])
    connection = connect(database_path)
    try:
        connection.execute(
            f"UPDATE documents SET {', '.join(f'{key} = ?' for key in fields)} WHERE id = ?",
            (*fields.values(), document_id),
        )
        connection.commit()
    finally:
        connection.close()


def _document(row: sqlite3.Row) -> dict:
    return {**dict(row), "findings": json.loads(row["findings"]) if row["findings"] else []}


def documents(database_path: Path, funda_id: str) -> list[dict]:
    """A Listing's Documents in the order they were added."""
    connection = connect(database_path)
    try:
        rows = connection.execute(
            "SELECT * FROM documents WHERE funda_id = ? ORDER BY id", (funda_id,)
        ).fetchall()
    finally:
        connection.close()
    return [_document(row) for row in rows]


def get_document(database_path: Path, funda_id: str, document_id: int) -> dict | None:
    return next((d for d in documents(database_path, funda_id) if d["id"] == document_id), None)


def delete_document(database_path: Path, document_id: int) -> None:
    connection = connect(database_path)
    try:
        connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        connection.commit()
    finally:
        connection.close()


def cached_extraction(database_path: Path, sha256: str, model: str | None) -> dict | None:
    """An earlier analysis of the same bytes by the same model, from any Listing."""
    connection = connect(database_path)
    try:
        row = connection.execute(
            "SELECT * FROM documents WHERE sha256 = ? AND model IS ? AND status = 'analysed' "
            "ORDER BY id DESC LIMIT 1",
            (sha256, model),
        ).fetchone()
    finally:
        connection.close()
    return _document(row) if row else None


def _address_key(address: str) -> str:
    return " ".join(address.casefold().split())


def cached_geocode(database_path: Path, address: str) -> tuple[float, float] | None:
    """A commute destination's (latitude, longitude) from an earlier lookup, by address ignoring
    case and spacing. Kept locally; the address never leaves except to the geocoder."""
    connection = connect(database_path)
    try:
        row = connection.execute(
            "SELECT latitude, longitude FROM geocodes WHERE address = ?", (_address_key(address),)
        ).fetchone()
    finally:
        connection.close()
    return (row["latitude"], row["longitude"]) if row else None


def cache_geocode(database_path: Path, address: str, place: tuple[float, float]) -> None:
    connection = connect(database_path)
    try:
        connection.execute(
            "INSERT OR REPLACE INTO geocodes (address, latitude, longitude) VALUES (?, ?, ?)",
            (_address_key(address), *place),
        )
        connection.commit()
    finally:
        connection.close()


def listings_with_verdicts(database_path: Path) -> list[str]:
    connection = connect(database_path)
    try:
        return [
            row["funda_id"]
            for row in connection.execute("SELECT DISTINCT funda_id FROM verdicts ORDER BY funda_id")
        ]
    finally:
        connection.close()
