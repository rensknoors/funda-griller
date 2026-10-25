"""Gemini adapter for the LLM client port, over the Gemini API's REST endpoint.

Model ids for the vision and Verdict roles come from configuration and are independent. The HTTP
call goes through `transport` so tests can replace it; the default uses the standard library.
"""

import base64
import json
import urllib.request
from collections.abc import Callable
from pathlib import Path

from app.ports import LlmError

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
TIMEOUT_SECONDS = 120

Transport = Callable[[str, dict, bytes], bytes]

VERDICT_INSTRUCTION = """\
You rate one house for one Dutch household. The input is JSON with two parts: `case`, the
deterministic evidence file (facts, computed metrics, affordability and Flags), and `buyer_profile`,
the household's derived figures and preferences.

Every fact carries a `provenance`; `case.provenance_legend` says how far each class can be trusted.
Weigh seller-stated and estimated facts below official registers, and say so when a conclusion rests
on a weak source.

Answer with:
- `tier`: one of must_buy, consider, skip, hard_no.
- `summary`: one sentence.
- `reasoning`: plain-language prose that cites the Flags it relies on.
- `cited_flags`: the `id` of every Flag from `case.flags` the reasoning relies on. Never invent ids.
- `bid_advice` for must_buy and consider (optional for skip, null for hard_no): `opening_bid` and
  `walk_away_maximum` in whole euros, and `conditions` (e.g. financieringsvoorbehoud, bouwkundige
  keuring, follow-ups on seller Documents). The walk-away maximum must not exceed
  `case.affordability.max_price` and the opening bid must not exceed the walk-away maximum.

Write summary, reasoning and conditions in Dutch.
"""

_VERDICT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "tier": {"type": "STRING", "enum": ["must_buy", "consider", "skip", "hard_no"]},
        "summary": {"type": "STRING"},
        "reasoning": {"type": "STRING"},
        "cited_flags": {"type": "ARRAY", "items": {"type": "STRING"}},
        "bid_advice": {
            "type": "OBJECT",
            "nullable": True,
            "properties": {
                "opening_bid": {"type": "INTEGER"},
                "walk_away_maximum": {"type": "INTEGER"},
                "conditions": {"type": "ARRAY", "items": {"type": "STRING"}},
            },
            "required": ["opening_bid", "walk_away_maximum", "conditions"],
        },
    },
    "required": ["tier", "summary", "reasoning", "cited_flags", "bid_advice"],
}


OBSERVATION_INSTRUCTION = """\
You inspect the photos of one Dutch house for sale. Each photo follows a text part `Foto n`; cite
photos by that number. Report only what the photos show; leave out anything you cannot see.

Report each of these at most once:
- `kitchen_age_years`, `bathroom_age_years`: estimated age in whole years, in `years`.
- `damp_or_mould`: `present` true when damp stains or mould are visible, false when the relevant
  walls and ceilings are visible and clean.
- `roof_condition`, `facade_condition`: `level` good, fair or poor.
- `renovation_needed`: `level` none, cosmetic, partial or full.

Every observation lists the `photos` it rests on and a short `note` in Dutch saying what you saw.
"""

_OBSERVATION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "observations": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "key": {
                        "type": "STRING",
                        "enum": [
                            "kitchen_age_years",
                            "bathroom_age_years",
                            "damp_or_mould",
                            "roof_condition",
                            "facade_condition",
                            "renovation_needed",
                        ],
                    },
                    "years": {"type": "INTEGER", "nullable": True},
                    "present": {"type": "BOOLEAN", "nullable": True},
                    "level": {
                        "type": "STRING",
                        "nullable": True,
                        "enum": ["good", "fair", "poor", "none", "cosmetic", "partial", "full"],
                    },
                    "photos": {"type": "ARRAY", "items": {"type": "INTEGER"}},
                    "note": {"type": "STRING"},
                },
                "required": ["key", "photos"],
            },
        }
    },
    "required": ["observations"],
}

# Which reply field carries each observation's value.
_OBSERVATION_VALUE_FIELD = {
    "kitchen_age_years": "years",
    "bathroom_age_years": "years",
    "damp_or_mould": "present",
    "roof_condition": "level",
    "facade_condition": "level",
    "renovation_needed": "level",
}

# Gemini caps an inline request at 20 MB; base64 adds a third, so batches stay under 14 MB of photos.
INLINE_LIMIT_BYTES = 14 * 1024 * 1024

_MIME_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def _observation(item: dict, offset: int) -> dict:
    """One reply item in the port's shape, its photo numbers shifted from batch to whole set.
    Values are passed through as given; the Observation service validates them."""
    key = item.get("key")
    photos = item.get("photos")
    return {
        "key": key,
        "value": item.get(_OBSERVATION_VALUE_FIELD.get(key, ""), None),
        "photos": [n + offset if isinstance(n, int) else n for n in photos] if isinstance(photos, list) else photos,
        "note": item.get("note"),
    }


def _urllib_transport(url: str, headers: dict, body: bytes) -> bytes:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read()


class GeminiLlmClient:
    def __init__(
        self,
        api_key: str | None,
        vision_model: str | None,
        verdict_model: str | None,
        transport: Transport = _urllib_transport,
        inline_limit_bytes: int = INLINE_LIMIT_BYTES,
    ) -> None:
        self.api_key = api_key
        self.vision_model = vision_model
        self.verdict_model = verdict_model
        self.transport = transport
        self.inline_limit_bytes = inline_limit_bytes

    def observe_photos(self, photo_paths: list[str]) -> list[dict]:
        """Observations over the whole photo set, photos numbered from 1 in the given order. A set
        too large for one inline request goes in batches, renumbered back to the whole set."""
        observations: list[dict] = []
        offset = 0
        for batch in self._photo_batches(photo_paths):
            parts: list[dict] = []
            for number, (path, content) in enumerate(batch, start=1):
                mime_type = _MIME_TYPES.get(Path(path).suffix.lower(), "image/jpeg")
                parts.append({"text": f"Foto {number}"})
                parts.append(
                    {"inlineData": {"mimeType": mime_type, "data": base64.b64encode(content).decode()}}
                )
            text = self._generate(self.vision_model, OBSERVATION_INSTRUCTION, parts, _OBSERVATION_SCHEMA)
            try:
                reply = json.loads(text)["observations"]
            except (json.JSONDecodeError, KeyError, TypeError) as error:
                raise LlmError("observation reply is not the expected JSON") from error
            observations += [_observation(item, offset) for item in reply if isinstance(item, dict)]
            offset += len(batch)
        return observations

    def _photo_batches(self, photo_paths: list[str]) -> list[list[tuple[str, bytes]]]:
        batches: list[list[tuple[str, bytes]]] = [[]]
        size = 0
        for path in photo_paths:
            try:
                content = Path(path).read_bytes()
            except OSError as error:
                raise LlmError("photo unreadable") from error
            if batches[-1] and size + len(content) > self.inline_limit_bytes:
                batches.append([])
                size = 0
            batches[-1].append((path, content))
            size += len(content)
        return [batch for batch in batches if batch]

    def extract_findings(self, document_path: str) -> list[dict]:
        raise NotImplementedError("Findings arrive with ticket 12")

    def rate(self, case: dict, buyer_profile: dict) -> dict:
        text = self._generate(
            self.verdict_model,
            VERDICT_INSTRUCTION,
            json.dumps({"case": case, "buyer_profile": buyer_profile}, ensure_ascii=False),
            _VERDICT_SCHEMA,
        )
        try:
            return json.loads(text)
        except json.JSONDecodeError as error:
            raise LlmError("reply is not JSON") from error

    def _generate(
        self, model: str | None, instruction: str, prompt: str | list[dict], schema: dict
    ) -> str:
        """`prompt` is the user text, or the user parts (e.g. text and inline images) as is."""
        if not self.api_key:
            raise LlmError("no Gemini API key configured")
        if not model:
            raise LlmError("no model configured")
        parts = [{"text": prompt}] if isinstance(prompt, str) else prompt
        body = {
            "systemInstruction": {"parts": [{"text": instruction}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema},
        }
        try:
            raw = self.transport(
                f"{API_ROOT}/models/{model}:generateContent",
                {"Content-Type": "application/json", "x-goog-api-key": self.api_key},
                json.dumps(body).encode(),
            )
            reply = json.loads(raw)
            return reply["candidates"][0]["content"]["parts"][0]["text"]
        except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
            raise LlmError(f"Gemini call failed: {type(error).__name__}") from error
