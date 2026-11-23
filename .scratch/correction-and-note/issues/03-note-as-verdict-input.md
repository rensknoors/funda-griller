# 03: Notitie as an input to the Oordeel

**Type:** task

**Blocked by:** none

**Status:** ready-for-agent

**What to build:** ADR-0006, spec decision 9. One editable free text per house, outside the Case, which the model reads and weighs for the Oordeel and the Biedadvies. It raises no Flag and never forces a Harde afwijzing. A change makes the Oordeel Achterhaald with the new cause `note`. In the UI it is a text field on the Woning page, visible from both the Dossier and the Oordeel tab (e.g. under the Woning header). Follow `DESIGN.md`.

- [ ] Storage of one text per house with `updated_at`; `PUT /listings/{funda_id}/note`; an empty text clears it
- [ ] The Verdict prompt receives the Notitie as a separate, labelled input; it never appears in the Case's `facts` and `flags` never read it
- [ ] `built_from.note_updated_at`; `changed_inputs` reports `note`; the UI words it among the causes of Achterhaald
- [ ] Notitie field on the Woning page, reachable from both tabs, saving without a page reload
- [ ] Regression case: a Notitie that should move the Oordeel (e.g. a neighbour reports foundation problems)
- [ ] `VERDICT_PROMPT_VERSION` bumped

## Comments
