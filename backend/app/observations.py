"""Observations (Waarnemingen): condition signals a vision model reads from a snapshot's photos.

Extraction is fact-gathering, not judgement (ADR-0001): it runs once per photo set, its result is
stored with the photos it cites, and it is reused until the user asks for a re-run. The model's
answer is validated here; an observation with an unknown key, a value of the wrong kind or a photo
reference that does not exist is dropped, never stored.
"""

from collections.abc import Callable
from pathlib import Path

from app import store
from app.photos import photo_set
from app.ports import LlmClient

CONDITIONS = ("good", "fair", "poor")
RENOVATION_LEVELS = ("none", "cosmetic", "partial", "full")


def _years(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 200


def _one_of(choices: tuple[str, ...]) -> Callable[[object], bool]:
    return lambda value: value in choices


# What the vision model may observe, with the kind of value each takes. The LLM client port's
# `observe_photos` answers with `{key, value, photos: [photo numbers from 1], note}` items.
OBSERVATION_KINDS: dict[str, Callable[[object], bool]] = {
    "kitchen_age_years": _years,
    "bathroom_age_years": _years,
    "damp_or_mould": lambda value: isinstance(value, bool),
    "roof_condition": _one_of(CONDITIONS),
    "facade_condition": _one_of(CONDITIONS),
    "renovation_needed": _one_of(RENOVATION_LEVELS),
}


def validated(answer: object, photo_count: int) -> list[dict]:
    """The well-formed observations from the model's answer; the first per key wins."""
    kept: dict[str, dict] = {}
    for item in answer if isinstance(answer, list) else []:
        if not isinstance(item, dict):
            continue
        key, value, photos = item.get("key"), item.get("value"), item.get("photos")
        if key not in OBSERVATION_KINDS or key in kept or not OBSERVATION_KINDS[key](value):
            continue
        if not isinstance(photos, list) or not photos:
            continue
        if not all(isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= photo_count for n in photos):
            continue
        note = item.get("note")
        kept[key] = {
            "key": key,
            "value": value,
            "photos": sorted(set(photos)),
            "note": note.strip() if isinstance(note, str) and note.strip() else None,
        }
    return list(kept.values())


def observe(
    database_path: Path,
    media_dir: Path,
    llm_client: LlmClient | None,
    model: str | None,
    funda_id: str,
    photos: list[dict],
    attempted_at: str,
    rerun: bool = False,
) -> str | None:
    """Run the vision model over the photos unless this photo set already has Observations (or
    `rerun` asks again). Returns the run's outcome, or None when nothing ran."""
    identity = photo_set(photos)
    if identity is None or llm_client is None:
        return None
    if not rerun and store.observation_runs(database_path, funda_id, identity)["last_success"]:
        return None
    paths = [store.photo_path(media_dir, funda_id, photo["name"]) for photo in photos]
    if any(path is None for path in paths):
        store.add_observation_run(
            database_path, funda_id, identity, attempted_at, "failed", model, "photo_missing"
        )
        return "failed"
    try:
        answer = llm_client.observe_photos([str(path) for path in paths])
    except Exception as error:  # noqa: BLE001 - a failed analysis never fails the caller
        store.add_observation_run(
            database_path, funda_id, identity, attempted_at, "failed", model, type(error).__name__
        )
        return "failed"
    store.add_observation_run(
        database_path,
        funda_id,
        identity,
        attempted_at,
        "succeeded",
        model,
        observations=validated(answer, len(photos)),
    )
    return "succeeded"
