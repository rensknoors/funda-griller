"""Gemini adapter for the LLM client port, over the Gemini API's REST endpoint.

Model ids for the vision and Verdict roles come from configuration and are independent. The HTTP
call goes through `transport` so tests can replace it; the default uses the standard library.
"""

import base64
import io
import json
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError

from app.findings import TOPICS
from app.ports import LlmError

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
TIMEOUT_SECONDS = 120

Transport = Callable[[str, dict, bytes], bytes]

# Bump on any change to VERDICT_INSTRUCTION or the Verdict schema; the regression set records it.
VERDICT_PROMPT_VERSION = 4

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
- `bid_advice` for must_buy and consider (optional for skip, null for hard_no): `opening_bid` in
  whole euros and `conditions` (e.g. financieringsvoorbehoud, bouwkundige keuring, follow-ups on
  seller Documents).

The walk-away maximum is already set: `case.walk_away.walk_away_maximum`, derived from comparables
and affordability (`case.walk_away` says how). Do not propose your own. The opening bid must not
exceed it. When `case.walk_away.weakly_grounded` is true there are too few comparables and it rests
on the asking price (or affordability alone); say in the reasoning that the bid advice is weakly
grounded.

`case.renovation_estimate` is what the house may cost to renovate, from a versioned cost table:
items in three classes (`direct`: Direct nodig, `within_5_years`: Binnen 5 jaar, `optional`:
Optioneel), each a low-high range of public average prices, estimated, citing the facts that
triggered it (inspection items rest on the build year alone). The Direct nodig midpoint is already
taken off the affordable maximum and the walk-away basis (`case.walk_away.renovation_direct`); do not
subtract it again. Weigh the estimate against `buyer_profile.renovation_tolerance`, and name
`missing_inputs` (no photos read, no Vragenlijst, no energielabel) as gaps in what is known.

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
                "conditions": {"type": "ARRAY", "items": {"type": "STRING"}},
            },
            "required": ["opening_bid", "conditions"],
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


FINDINGS_INSTRUCTION = """\
You read one Dutch house-sale Document from the seller or selling agent: a Vragenlijst (seller
questionnaire), a Lijst van zaken (what stays and what goes), a funda brochure or similar. Extract
what the seller states about the house as Findings. Look in particular for asbestos, leaks and damp,
foundation problems, leased solar panels (or other leased installations), erfpacht (with canon and
term when stated), subsidies tied to the house, notable items that stay or go, and the age or state of
the cv-ketel (`boiler_old`: present when the seller states it is over 15 years old or due for
replacement) and the electrical wiring (`wiring_old`: present when the seller states it is old,
original or due for renewal).

For each Finding give:
- `topic`: one of the listed topics; use `other` for anything else worth knowing.
- `present`: true when the seller states it applies to the house, false when the seller states it
  does not (e.g. "Asbest aanwezig? Nee").
- `statement`: one short sentence in Dutch saying what the seller states, close to their words.
- `quote`: the words on the page the Finding rests on, copied exactly (a few words to one
  sentence). It is checked against the page's text; a Finding whose quote is not there is dropped.
- `page`: the number from the `[PAGE n]` label in front of the page the quote is on (not the
  number printed on the page).

Only report what the Document says. Never guess, and leave out marketing language.
"""

_FINDINGS_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "findings": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "topic": {"type": "STRING", "enum": list(TOPICS)},
                    "present": {"type": "BOOLEAN"},
                    "statement": {"type": "STRING"},
                    "quote": {"type": "STRING"},
                    "page": {"type": "INTEGER"},
                },
                "required": ["topic", "present", "statement", "quote", "page"],
            },
        }
    },
    "required": ["findings"],
}


def _pages(content: bytes) -> list[bytes]:
    """Each page of the PDF as a PDF of its own."""
    try:
        reader = PdfReader(io.BytesIO(content))
        pages = []
        for page in reader.pages:
            writer = PdfWriter()
            writer.add_page(page)
            out = io.BytesIO()
            writer.write(out)
            pages.append(out.getvalue())
    except (PyPdfError, ValueError, KeyError, TypeError, OSError) as error:
        raise LlmError("Document cannot be split into pages") from error
    return pages


def _google_message(error: urllib.error.HTTPError) -> str:
    """Google's own explanation from the error body (e.g. an unknown model), or the HTTP reason."""
    try:
        return json.loads(error.read())["error"]["message"]
    except (OSError, ValueError, KeyError, TypeError):
        return str(error.reason)


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
        """The PDF goes to the vision model split into single pages, each after a `[PAGE n]` label,
        so a Finding's page is the label it quotes from; the caller verifies quotes and pages."""
        try:
            content = Path(document_path).read_bytes()
        except OSError as error:
            raise LlmError("Document cannot be read") from error
        if len(content) > self.inline_limit_bytes:
            # Larger Documents need the Files API, which is not built yet.
            raise LlmError("Document too large to send inline")
        pages = _pages(content)
        if sum(len(page) for page in pages) > self.inline_limit_bytes:
            raise LlmError("Document too large to send inline")
        parts: list[dict] = []
        for number, page in enumerate(pages, start=1):
            parts.append({"text": f"[PAGE {number}]"})
            parts.append({"inlineData": {"mimeType": "application/pdf", "data": base64.b64encode(page).decode()}})
        parts.append({"text": "Extract the Findings from this Document, each with its quote and page label."})
        text = self._generate(self.vision_model, FINDINGS_INSTRUCTION, parts, _FINDINGS_SCHEMA)
        try:
            findings = json.loads(text)["findings"]
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            raise LlmError("reply has no findings") from error
        if not isinstance(findings, list):
            raise LlmError("reply has no findings")
        return findings

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
        except urllib.error.HTTPError as error:
            raise LlmError(f"Gemini call failed: HTTP {error.code}: {_google_message(error)}") from error
        except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
            raise LlmError(f"Gemini call failed: {type(error).__name__}") from error
