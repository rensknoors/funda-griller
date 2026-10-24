"""The Gemini adapter, driven through a fake HTTP transport: no network."""

import json

import pytest

from app.gemini_client import GeminiLlmClient
from app.ports import LlmError

CASE = {
    "funda_id": "80907644",
    "facts": [{"key": "asking_price", "value": 595_000, "provenance": "listing"}],
    "flags": [],
    "provenance_legend": {"listing": "Stated in the funda Listing; not verified."},
}
PROFILE = {"profile_version": 1, "must_haves": ["Tuin"]}
ANSWER = {
    "tier": "consider",
    "summary": "Prima woning.",
    "reasoning": "Past bij jullie wensen.",
    "cited_flags": [],
    "bid_advice": {"opening_bid": 585_000, "walk_away_maximum": 610_000, "conditions": ["Keuring"]},
}


class FakeTransport:
    def __init__(self, reply: bytes | Exception) -> None:
        self.reply = reply
        self.requests: list[tuple[str, dict, dict]] = []

    def __call__(self, url: str, headers: dict, body: bytes) -> bytes:
        self.requests.append((url, headers, json.loads(body)))
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def gemini_reply(text: str) -> bytes:
    return json.dumps({"candidates": [{"content": {"parts": [{"text": text}]}}]}).encode()


def client_with(reply, api_key="key-123") -> tuple[GeminiLlmClient, FakeTransport]:
    transport = FakeTransport(reply)
    return GeminiLlmClient(api_key, "vision-model", "verdict-model", transport), transport


def test_rating_asks_the_configured_verdict_model_for_structured_json():
    client, transport = client_with(gemini_reply(json.dumps(ANSWER)))

    answer = client.rate(CASE, PROFILE)

    assert answer == ANSWER
    [(url, headers, body)] = transport.requests
    assert url.endswith("/models/verdict-model:generateContent")
    assert headers["x-goog-api-key"] == "key-123"
    assert "key-123" not in url
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert body["generationConfig"]["responseSchema"]["properties"]["tier"]["enum"] == [
        "must_buy",
        "consider",
        "skip",
        "hard_no",
    ]
    sent = body["contents"][0]["parts"][0]["text"]
    assert json.loads(sent) == {"case": CASE, "buyer_profile": PROFILE}


def test_an_unparseable_reply_is_an_llm_error():
    client, _ = client_with(gemini_reply("not json"))

    with pytest.raises(LlmError):
        client.rate(CASE, PROFILE)


def test_a_reply_without_candidates_is_an_llm_error():
    client, _ = client_with(json.dumps({"promptFeedback": {"blockReason": "SAFETY"}}).encode())

    with pytest.raises(LlmError):
        client.rate(CASE, PROFILE)


def test_a_transport_failure_is_an_llm_error():
    client, _ = client_with(OSError("connection refused"))

    with pytest.raises(LlmError):
        client.rate(CASE, PROFILE)


def test_without_an_api_key_nothing_is_sent():
    client, transport = client_with(gemini_reply("{}"), api_key=None)

    with pytest.raises(LlmError):
        client.rate(CASE, PROFILE)
    assert transport.requests == []
