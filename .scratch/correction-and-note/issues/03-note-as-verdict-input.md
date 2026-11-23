# 03: Notitie as an input to the Oordeel

**Type:** task

**Blocked by:** none

**Status:** resolved

**What to build:** ADR-0006, spec decision 9. One editable free text per house, outside the Case, which the model reads and weighs for the Oordeel and the Biedadvies. It raises no Flag and never forces a Harde afwijzing. A change makes the Oordeel Achterhaald with the new cause `note`. In the UI it is a text field on the Woning page, visible from both the Dossier and the Oordeel tab (e.g. under the Woning header). Follow `DESIGN.md`.

- [x] Storage of one text per house with `updated_at`; `PUT /listings/{funda_id}/note`; an empty text clears it
- [x] The Verdict prompt receives the Notitie as a separate, labelled input; it never appears in the Case's `facts` and `flags` never read it
- [x] `built_from.note_updated_at`; `changed_inputs` reports `note`; the UI words it among the causes of Achterhaald
- [x] Notitie field on the Woning page, reachable from both tabs, saving without a page reload
- [x] Regression case: a Notitie that should move the Oordeel (e.g. a neighbour reports foundation problems)
- [x] `VERDICT_PROMPT_VERSION` bumped

## Comments

Built test-first through the HTTP API (`backend/tests/test_note_api.py`) and one Playwright spec (`frontend/e2e/woning-notitie.spec.ts`). The Note is stored in a `notes` table (`GET`/`PUT /api/listings/{funda_id}/note`). It reaches the model through a third argument of the LLM client port's `rate`, which Gemini receives as a `note` part beside `case` and `buyer_profile` (prompt version 13). `changed_inputs` compares `built_from.note_updated_at`; Verdicts from before the Note read as made without one. In the regression set the house's Note is `house_note`, since `note` there already holds why the tier is expected. `example-note-foundation-problems` is `example-efficient-family-home` plus a neighbour's report of foundation problems, expected skip. The UI is a Notitie band under the Dossier/Oordeel tabs; saving re-reads the Oordeel in place, which then says it rests on an older version of "je notitie". The Markdown export is ticket 04.
- 2026-11-23, review fixes: a deterministic Hard no is no longer made Achterhaald by a Note change (`changed_inputs` skips `note` for it, as it does `model`). The regression harness reads the Note through `store.note_text`.
