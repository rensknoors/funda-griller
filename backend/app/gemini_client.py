"""Gemini adapter for the LLM client port, over the Gemini API's REST endpoint.

Model ids for the vision and Verdict roles come from configuration and are independent. The HTTP
call goes through `transport` so tests can replace it; the default uses the standard library.
"""

import json
import urllib.request
from collections.abc import Callable

from app.ports import LlmError

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
TIMEOUT_SECONDS = 120

Transport = Callable[[str, dict, bytes], bytes]

# Bump on any change to VERDICT_INSTRUCTION or the Verdict schema; the regression set records it.
VERDICT_PROMPT_VERSION = 1

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
  keuring, follow-ups on seller Documents). Derive the walk-away maximum from the comparables
  (`case.metrics.asking_vs_comparables`) and affordability. It must not exceed
  `case.bid_limits.affordable_maximum`, nor `case.bid_limits.comparables_maximum` when that is set
  (it is null when comparables are thin or missing), and the opening bid must not exceed the
  walk-away maximum.

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
    ) -> None:
        self.api_key = api_key
        self.vision_model = vision_model
        self.verdict_model = verdict_model
        self.transport = transport

    def observe_photos(self, photo_paths: list[str]) -> list[dict]:
        raise NotImplementedError("Observations arrive with ticket 11")

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

    def _generate(self, model: str | None, instruction: str, prompt: str, schema: dict) -> str:
        if not self.api_key:
            raise LlmError("no Gemini API key configured")
        if not model:
            raise LlmError("no model configured")
        body = {
            "systemInstruction": {"parts": [{"text": instruction}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
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
