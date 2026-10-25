"""Listing photos kept on disk with the snapshot, so they survive the Listing going offline.

Photos are only ever served by the app's own UI. A photo that cannot be downloaded is left out of
the snapshot; the capture itself never fails on it.
"""

import hashlib
from pathlib import Path
from urllib.parse import urlparse

from app import store
from app.ports import PhotoDownloader


def app_url(funda_id: str, name: str) -> str:
    return f"/api/listings/{funda_id}/photos/{name}"


def keep_photos(
    media_dir: Path,
    downloader: PhotoDownloader | None,
    funda_id: str,
    photo_urls: tuple[str, ...],
    previous: list[dict],
) -> list[dict]:
    """The snapshot's photos, numbered from 1 in Listing order. A photo already uploaded to the app
    (manual entry) is used as is; one downloaded for an earlier snapshot is reused, not fetched again."""
    local_prefix = app_url(funda_id, "")
    earlier = {photo["source_url"]: photo["name"] for photo in previous if photo.get("source_url")}
    kept: list[tuple[str, str | None]] = []
    for url in photo_urls:
        if url.startswith(local_prefix):
            kept.append((url.removeprefix(local_prefix), None))
            continue
        name = earlier.get(url)
        if name is None or store.photo_path(media_dir, funda_id, name) is None:
            name = _download(media_dir, downloader, funda_id, url)
        if name is not None:
            kept.append((name, url))
    photos = []
    for name, source_url in kept:
        path = store.photo_path(media_dir, funda_id, name)
        if path is None:
            continue
        photos.append(
            {
                "number": len(photos) + 1,
                "name": name,
                "url": app_url(funda_id, name),
                "source_url": source_url,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return photos


def photo_set(photos: list[dict]) -> str | None:
    """Identifies a set of photos by content and order; None when there are none."""
    if not photos:
        return None
    return hashlib.sha256("\n".join(photo["sha256"] for photo in photos).encode()).hexdigest()


def _download(
    media_dir: Path, downloader: PhotoDownloader | None, funda_id: str, url: str
) -> str | None:
    if downloader is None:
        return None
    try:
        content = downloader.download(url)
    except Exception:  # noqa: BLE001 - an unavailable photo is left out, never fails the capture
        return None
    if not content:
        return None
    return store.save_photo(media_dir, funda_id, Path(urlparse(url).path).name, content)
