"""The Gemini adapter, driven through a fake HTTP transport: no network."""

import base64
import io
import json

import urllib.error

import pytest

from pypdf import PdfReader

from app.gemini_client import GeminiLlmClient
from app.ports import LlmError
from tests.pdf_fixtures import VRAGENLIJST

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
    "bid_advice": {"opening_bid": 585_000, "conditions": ["Keuring"]},
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
    sent = body["contents"][0]["parts"][0]["text"]
    assert json.loads(sent) == {"case": CASE, "buyer_profile": PROFILE}


def test_the_verdict_model_is_not_asked_for_a_walk_away_maximum():
    client, transport = client_with(gemini_reply(json.dumps(ANSWER)))

    client.rate(CASE, PROFILE)

    [(_, _, body)] = transport.requests
    bid_advice = body["generationConfig"]["responseSchema"]["properties"]["bid_advice"]
    assert set(bid_advice["properties"]) == {"opening_bid", "conditions"}


def test_an_unparseable_reply_is_an_llm_error():
    client, _ = client_with(gemini_reply("not json"))

    with pytest.raises(LlmError):
        client.rate(CASE, PROFILE)


def test_a_reply_without_candidates_is_an_llm_error():
    client, _ = client_with(json.dumps({"promptFeedback": {"blockReason": "SAFETY"}}).encode())

    with pytest.raises(LlmError):
        client.rate(CASE, PROFILE)


def test_an_http_error_names_the_status_and_googles_message():
    body = json.dumps({"error": {"code": 404, "message": "models/verdict-model is not found"}}).encode()
    error = urllib.error.HTTPError("https://example", 404, "Not Found", {}, io.BytesIO(body))
    client, _ = client_with(error)

    with pytest.raises(LlmError, match="404.*models/verdict-model is not found"):
        client.rate(CASE, PROFILE)


def test_a_missing_api_key_says_so():
    client, _ = client_with(gemini_reply(json.dumps(ANSWER)), api_key=None)

    with pytest.raises(LlmError, match="no Gemini API key"):
        client.rate(CASE, PROFILE)


def test_a_transport_failure_is_an_llm_error():
    client, _ = client_with(OSError("connection refused"))

    with pytest.raises(LlmError):
        client.rate(CASE, PROFILE)


FINDING = {
    "topic": "asbestos",
    "present": True,
    "statement": "Asbest in de schuur.",
    "quote": "Ja, in de dakplaten van de schuur.",
    "page": 2,
}


def test_findings_are_extracted_by_the_vision_model_from_the_pdf_split_into_labelled_pages(tmp_path):
    document = tmp_path / "vragenlijst.pdf"
    document.write_bytes(VRAGENLIJST)
    client, transport = client_with(gemini_reply(json.dumps({"findings": [FINDING]})))

    findings = client.extract_findings(str(document))

    assert findings == [FINDING]
    [(url, _headers, body)] = transport.requests
    assert url.endswith("/models/vision-model:generateContent")
    parts = body["contents"][0]["parts"]
    labels = [part["text"] for part in parts if "text" in part and part["text"].startswith("[PAGE")]
    pages = [
        PdfReader(io.BytesIO(base64.b64decode(part["inlineData"]["data"])))
        for part in parts
        if "inlineData" in part
    ]
    assert labels == ["[PAGE 1]", "[PAGE 2]", "[PAGE 3]"]
    assert all(part["inlineData"]["mimeType"] == "application/pdf" for part in parts if "inlineData" in part)
    assert [len(page.pages) for page in pages] == [1, 1, 1]
    assert "asbest" in pages[1].pages[0].extract_text()


def test_a_findings_reply_without_a_list_is_an_llm_error(tmp_path):
    document = tmp_path / "vragenlijst.pdf"
    document.write_bytes(VRAGENLIJST)
    client, _ = client_with(gemini_reply(json.dumps({"nope": 1})))

    with pytest.raises(LlmError):
        client.extract_findings(str(document))


def test_a_document_too_large_to_send_inline_is_an_llm_error(tmp_path):
    document = tmp_path / "huge.pdf"
    document.write_bytes(b"%PDF-1.4\n" + b"0" * (15 * 1024 * 1024))
    client, transport = client_with(gemini_reply("{}"))

    with pytest.raises(LlmError):
        client.extract_findings(str(document))
    assert transport.requests == []


def photos(tmp_path, *contents: bytes) -> list[str]:
    paths = []
    for number, content in enumerate(contents, start=1):
        path = tmp_path / f"photo{number}.jpg"
        path.write_bytes(content)
        paths.append(str(path))
    return paths


def test_observing_sends_every_photo_numbered_to_the_vision_model(tmp_path):
    reply = {
        "observations": [
            {"key": "kitchen_age_years", "years": 25, "photos": [2], "note": "Oude keuken"},
            {"key": "damp_or_mould", "present": True, "photos": [1]},
            {"key": "roof_condition", "level": "poor", "photos": [1, 2]},
        ]
    }
    client, transport = client_with(gemini_reply(json.dumps(reply)))

    observations = client.observe_photos(photos(tmp_path, b"gevel", b"keuken"))

    assert observations == [
        {"key": "kitchen_age_years", "value": 25, "photos": [2], "note": "Oude keuken"},
        {"key": "damp_or_mould", "value": True, "photos": [1], "note": None},
        {"key": "roof_condition", "value": "poor", "photos": [1, 2], "note": None},
    ]
    [(url, _, body)] = transport.requests
    assert url.endswith("/models/vision-model:generateContent")
    parts = body["contents"][0]["parts"]
    labels = [part["text"] for part in parts if "text" in part]
    images = [base64.b64decode(part["inlineData"]["data"]) for part in parts if "inlineData" in part]
    assert labels == ["Foto 1", "Foto 2"]
    assert images == [b"gevel", b"keuken"]
    assert all(p["inlineData"]["mimeType"] == "image/jpeg" for p in parts if "inlineData" in p)


def test_a_large_photo_set_is_sent_in_batches_and_numbered_as_one_set(tmp_path):
    first = {"observations": [{"key": "facade_condition", "level": "fair", "photos": [2]}]}
    second = {"observations": [{"key": "kitchen_age_years", "years": 10, "photos": [1]}]}
    replies = iter([gemini_reply(json.dumps(first)), gemini_reply(json.dumps(second))])
    sent: list[list[str]] = []

    def transport(url, headers, body):
        parts = json.loads(body)["contents"][0]["parts"]
        sent.append([part["text"] for part in parts if "text" in part])
        return next(replies)

    client = GeminiLlmClient("key", "vision-model", "verdict-model", transport, inline_limit_bytes=12)

    observations = client.observe_photos(photos(tmp_path, b"123456", b"123456", b"123456"))

    assert sent == [["Foto 1", "Foto 2"], ["Foto 1"]]
    assert [(o["key"], o["photos"]) for o in observations] == [
        ("facade_condition", [2]),
        ("kitchen_age_years", [3]),
    ]


def test_an_unparseable_observation_reply_is_an_llm_error(tmp_path):
    client, _ = client_with(gemini_reply("not json"))

    with pytest.raises(LlmError):
        client.observe_photos(photos(tmp_path, b"gevel"))


def test_without_an_api_key_nothing_is_sent():
    client, transport = client_with(gemini_reply("{}"), api_key=None)

    with pytest.raises(LlmError):
        client.rate(CASE, PROFILE)
    assert transport.requests == []
