# 12: Documents and Findings

**What to build:** The user uploads seller and agent PDFs (Vragenlijst, Lijst van zaken, anything else) against a Listing, and the funda brochure is attached automatically. The model extracts Findings such as asbestos, leaks, leased solar panels, erfpacht, subsidies and what stays or goes, each with a page reference and a seller-stated mark. Findings feed Flags and the Verdict, and re-upload or removal rebuilds the Case.

**Blocked by:** 09 (Verdict and Bid Advice)

**Status:** resolved

- [x] Upload, list and remove Documents per Listing
- [x] The funda brochure is downloaded (with a browser user agent) and attached as a Document
- [x] Findings are extracted once per Document, cached, and each cites its page
- [x] Findings are marked seller-stated and rendered distinctly from Source facts
- [x] A Finding can raise a Flag through the rule set
- [x] Removing or re-uploading a Document rebuilds the Case without leftover Findings
- [x] An unreadable Document is reported as such, never silently treated as analysed
- [x] Documents are stored locally and shown only in the app's own UI
- [x] Tests use the fake LLM client; the real brochure from the prototype is used as a fixture

## Comments

- API: `GET/POST /api/listings/{id}/documents`, `PUT|DELETE .../documents/{doc}` (re-upload, remove), `POST .../documents/{doc}/analyse` (retry), `GET .../documents/{doc}/file` (inline, `no-store`). The Case gains `documents` and `built_from.documents`; a Document change marks the Verdict out of date (`case`).
- New port `DocumentDownloader` (`app/document_downloader.py`, browser user agent, https only). The brochure is fetched on capture, once per brochure URL; a new URL replaces the old brochure.
- Document states: `analysed`, `unreadable` (not a PDF, encrypted, corrupt; checked with pypdf before the LLM is called), `not_analysed` (no LLM or the call failed; retryable), `download_failed` (retryable).
- Findings: topic from a fixed list (`app/findings.py`), `present`, Dutch `statement`, 1-based PDF `page`. Findings with an unknown topic or a page outside the PDF are rejected and counted, never shown. Extraction is cached by content hash and model, across Listings.
- Flag rules (set version 4, after ticket 11's 3; store schema 7): the `equals` condition with `values = [true]` over `finding.<topic>`; risks for asbestos, leak, foundation and erfpacht, a con for leased solar panels, each with `deal_breaker_aliases` (erfpacht in a Document forces a Hard no for an erfpacht deal-breaker).
- Gemini: the whole PDF is sent inline to the vision-role model (up to 14 MB; larger needs the Files API, not built). Page references are range-checked, not verified against the page text.
- The real brochure is a third party's document and is not committed: tests read it from the gitignored `backend/tests/fixtures/local/brochure.pdf` (or `FG_BROCHURE_FIXTURE`) and skip without it. Copy it from the prototype's `PROTOTYPE_out_live/brochure.pdf`.
