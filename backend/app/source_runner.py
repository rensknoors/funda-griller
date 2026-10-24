"""Runs Source clients for a Listing and stores each run. A failing Source never fails the caller."""

from dataclasses import asdict
from pathlib import Path

from app import store
from app.ports import Listing, SourceClient, SourceFailed, SourceSkipped


def run_sources(
    database_path: Path,
    clients: dict[str, SourceClient],
    listing: Listing,
    attempted_at: str,
) -> None:
    for name, client in clients.items():
        try:
            facts = client.fetch(listing)
        except SourceSkipped as skipped:
            store.add_source_run(
                database_path, listing.funda_id, name, attempted_at, "skipped", skipped.reason
            )
        except SourceFailed as failed:
            store.add_source_run(
                database_path, listing.funda_id, name, attempted_at, "failed", str(failed) or None
            )
        except Exception as error:  # noqa: BLE001 - any client error degrades to a failed Source
            store.add_source_run(
                database_path, listing.funda_id, name, attempted_at, "failed", type(error).__name__
            )
        else:
            store.add_source_run(
                database_path,
                listing.funda_id,
                name,
                attempted_at,
                "succeeded",
                facts=[asdict(fact) for fact in facts],
            )
