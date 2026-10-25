"""Findings (Bevindingen): seller-stated facts extracted from Documents. Pure, no I/O, no judgement.

The LLM's raw extraction is validated here before anything stores it: a Finding names one of the
known topics, says whether the seller states it applies, and cites a page that exists in the
Document. Anything else is dropped and counted, never shown.
"""

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


def validated(raw: object, page_count: int) -> tuple[list[dict], int]:
    """The valid Findings in the model's answer, and how many were rejected."""
    items = raw if isinstance(raw, list) else []
    findings = []
    for item in items:
        finding = _finding(item, page_count)
        if finding is not None:
            findings.append(finding)
    return findings, len(items) - len(findings)


def _finding(item: object, page_count: int) -> dict | None:
    if not isinstance(item, dict):
        return None
    topic, present, statement, page = (item.get(k) for k in ("topic", "present", "statement", "page"))
    if topic not in TOPICS or not isinstance(present, bool):
        return None
    if not isinstance(statement, str) or not statement.strip():
        return None
    if isinstance(page, bool) or not isinstance(page, int) or not 1 <= page <= page_count:
        return None
    return {"topic": topic, "present": present, "statement": statement.strip(), "page": page}


def finding_facts(documents: Sequence[dict]) -> list[dict]:
    """Case facts from every analysed Document's Findings, each citing its Document and page."""
    return [
        {
            "key": finding["topic"],
            "value": finding["present"],
            "statement": finding["statement"],
            "page": finding["page"],
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
