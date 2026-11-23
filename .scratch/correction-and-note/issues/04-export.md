# 04: Correcties and Notitie in the Markdown export

**Type:** task

**Blocked by:** 01, 03

**Status:** resolved

**What to build:** Spec decision 10. The export shows each corrected fact with **gecorrigeerd**, the original value and the Toelichting. The Notitie appears in its own section. Neither is kept private.

- [x] Corrected facts in the export with the original value and the Toelichting
- [x] Notitie section, left out when the Notitie is empty
- [x] Export tests updated

## Comments

- 2026-11-23: Built test-first through `GET /api/listings/{funda_id}/export.md` (`backend/tests/test_export_api.py`). A corrected fact stays in Feiten > Advertentie, as `112 **gecorrigeerd** (advertentie: 152; toelichting: …)`; the original reads "onbekend" when the Listing left it out, "register" for a corrected energielabel the register had, and the line adds "de advertentie is gewijzigd sinds de correctie" when `listing_changed`. The Woning section shows the corrected area, year and label with the Listing's value beside it. The Notitie gets its own section, `## Notitie (van het huishouden)` right after Feiten, fenced and unaltered (also with `profile=false`); empty sections are now skipped by `render`. The preamble explains **Gecorrigeerd** and lists Correctie/Notitie in the Begrippen; Achterhaald names "de Notitie" for cause `note`.
