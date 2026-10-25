"""Reads a Document and has its Findings extracted once, through the LLM client port.

A Document ends in one of four states, so an unread one is never mistaken for an analysed one:
`analysed`, `unreadable` (not a PDF, encrypted or broken), `not_analysed` (no LLM client, or the
call failed; can be retried) or `download_failed` (the funda brochure could not be fetched).
Extraction is cached by content and model: the same bytes are never sent twice.
"""

import hashlib
import io
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from app import store
from app.findings import validated
from app.ports import DocumentDownloader, DownloadFailed, LlmClient, LlmError


def page_texts(content: bytes) -> tuple[list[str] | None, str | None]:
    """The PDF's text, one entry per page (empty for a page without a text layer), or None and
    why it cannot be read."""
    if not content.lstrip()[:5] == b"%PDF-":
        return None, "not_a_pdf"
    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            return None, "encrypted"
        texts = [page.extract_text() or "" for page in reader.pages]
    except (PyPdfError, ValueError, KeyError, TypeError, OSError):
        return None, "corrupt"
    return (texts, None) if texts else (None, "corrupt")


def store_content(
    database_path: Path,
    media_dir: Path,
    funda_id: str,
    document: dict,
    content: bytes,
    llm_client: LlmClient | None,
    model: str | None,
    now: str,
) -> None:
    """Replace a Document's file with `content` and analyse it; earlier Findings are dropped."""
    store.delete_document_file(media_dir, funda_id, document["stored_name"])
    stored_name = store.save_document_file(media_dir, funda_id, content)
    store.update_document(
        database_path,
        document["id"],
        stored_name=stored_name,
        sha256=hashlib.sha256(content).hexdigest(),
        findings=[],
        rejected_findings=0,
        model=None,
        extracted_at=None,
    )
    analyse(database_path, media_dir, funda_id, document["id"], llm_client, model, now)


def analyse(
    database_path: Path,
    media_dir: Path,
    funda_id: str,
    document_id: int,
    llm_client: LlmClient | None,
    model: str | None,
    now: str,
) -> None:
    document = store.get_document(database_path, funda_id, document_id)
    path = store.document_file_path(media_dir, funda_id, document["stored_name"])
    texts, reason = page_texts(path.read_bytes()) if path else (None, "missing")
    if texts is None:
        store.update_document(database_path, document_id, status="unreadable", reason=reason, page_count=None)
        return
    pages = len(texts)
    cached = store.cached_extraction(database_path, document["sha256"], model)
    # Findings extracted before quotes were checked against their page carry no `verified`; they
    # are extracted again rather than reused.
    if cached is not None and all("verified" in finding for finding in cached["findings"]):
        store.update_document(
            database_path,
            document_id,
            status="analysed",
            reason=None,
            page_count=pages,
            findings=cached["findings"],
            rejected_findings=cached["rejected_findings"],
            model=model,
            extracted_at=cached["extracted_at"],
        )
        return
    if llm_client is None:
        store.update_document(database_path, document_id, status="not_analysed", reason="llm_unavailable", page_count=pages)
        return
    try:
        raw = llm_client.extract_findings(str(path))
    except LlmError:
        store.update_document(database_path, document_id, status="not_analysed", reason="llm_failed", page_count=pages)
        return
    findings, rejected = validated(raw, texts)
    store.update_document(
        database_path,
        document_id,
        status="analysed",
        reason=None,
        page_count=pages,
        findings=findings,
        rejected_findings=rejected,
        model=model,
        extracted_at=now,
    )


def download_and_analyse(
    database_path: Path,
    media_dir: Path,
    funda_id: str,
    document: dict,
    downloader: DocumentDownloader,
    llm_client: LlmClient | None,
    model: str | None,
    now: str,
) -> None:
    """Fetch a downloaded Document (the funda brochure) from its URL and analyse it."""
    try:
        content = downloader.download(document["source_url"])
    except DownloadFailed:
        store.update_document(database_path, document["id"], status="download_failed", reason="download_failed")
        return
    store_content(database_path, media_dir, funda_id, document, content, llm_client, model, now)
