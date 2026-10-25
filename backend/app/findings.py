"""Findings (Bevindingen): seller-stated facts extracted from Documents. Pure, no I/O, no judgement.

The LLM's raw extraction is validated here before anything stores it: a Finding names one of the
known topics, says whether the seller states it applies, cites a page that exists in the Document,
and quotes text that is on that page. A page without a text layer (a scan) cannot be checked: its
Findings are kept and marked unverified. Anything else is dropped and counted, never shown.
"""

import re
from collections.abc import Sequence

# What a Finding can be about. `present` says whether the seller states it applies to the house
# (asbestos present, a past leak, leased solar panels, erfpacht, a subsidy to repay or transfer,
# something that stays or goes).
TOPICS = (
    "asbestos",
    "leak",
    "solar_lease",
    "erfpacht",
    "subsidy",
    "stays_or_goes",
    "foundation",
    "other",
)


def validated(raw: object, page_texts: Sequence[str]) -> tuple[list[dict], int]:
    """The valid Findings in the model's answer, and how many were rejected. `page_texts` is the
    Document's text, one entry per page."""
    items = raw if isinstance(raw, list) else []
    findings = []
    for item in items:
        finding = _finding(item, page_texts)
        if finding is not None:
            findings.append(finding)
    return findings, len(items) - len(findings)


def _normalised(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.casefold()))


def _finding(item: object, page_texts: Sequence[str]) -> dict | None:
    if not isinstance(item, dict):
        return None
    topic, present, statement, quote, page = (
        item.get(k) for k in ("topic", "present", "statement", "quote", "page")
    )
    if topic not in TOPICS or not isinstance(present, bool):
        return None
    if not isinstance(statement, str) or not statement.strip():
        return None
    if isinstance(page, bool) or not isinstance(page, int) or not 1 <= page <= len(page_texts):
        return None
    page_text = _normalised(page_texts[page - 1])
    quoted = _normalised(quote) if isinstance(quote, str) else ""
    if page_text and not (quoted and f" {quoted} " in f" {page_text} "):
        return None
    return {
        "topic": topic,
        "present": present,
        "statement": statement.strip(),
        "quote": quote.strip() if isinstance(quote, str) else None,
        "page": page,
        "verified": bool(page_text),
    }


def finding_facts(documents: Sequence[dict]) -> list[dict]:
    """Case facts from every analysed Document's Findings, each citing its Document and page."""
    return [
        {
            "key": finding["topic"],
            "value": finding["present"],
            "statement": finding["statement"],
            "quote": finding.get("quote"),
            "page": finding["page"],
            "verified": finding.get("verified", False),
            "provenance": "finding",
            "seller_stated": True,
            "document_id": document["id"],
            "document_name": document["name"],
            "extracted_at": document["extracted_at"],
        }
        for document in documents
        if document["status"] == "analysed"
        for finding in document["findings"]
    ]


def document_summaries(documents: Sequence[dict]) -> list[dict]:
    """What the Case says about each Document: enough to list it and report an unread one."""
    return [
        {
            "id": d["id"],
            "name": d["name"],
            "kind": d["kind"],
            "status": d["status"],
            "reason": d["reason"],
            "page_count": d["page_count"],
            "finding_count": len(d["findings"]),
            "rejected_findings": d["rejected_findings"],
            "added_at": d["added_at"],
            "extracted_at": d["extracted_at"],
        }
        for d in documents
    ]
