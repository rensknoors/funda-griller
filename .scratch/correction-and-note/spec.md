# Correction and Note: the household's own input per house

Decision record: `docs/adr/0006-note-outside-the-case.md`. Decisions settled with the user on 2026-11-23; see Decisions below.

## Problem Statement

The app trusts the Listing's facts. When the agent states one wrongly, the error spreads through everything derived from it. A concrete case is a living area of 128 m² that is really 112 m². The Expected Sale Price is the comparables' median €/m² × living area. A living area that is too large therefore inflates the Expected Sale Price and, through it, the Prijsstelling, the Walk-away Maximum, the Guide Bid and the price Flags or Hard no. It also distorts the Renovation Estimate's per-m² and size-band items. The user has no way to say "this is wrong" or to give the model what they learned at a viewing.

## Solution

Two concepts (glossary: **Correction**, **Note**):

1. **Correctie**: the user's own value for a Listing fact, with a required explanation. It is part of the Case, outranks every other value for that fact in every computation, and keeps the original visible.
2. **Notitie**: one free text per house, outside the Case, which the model reads and weighs for the Oordeel and Biedadvies.

## User Stories

1. As a buyer, I want to correct a wrong living area so the Verwachte verkoopprijs, the Maximumbod and the Richtbod are computed on the real size.
2. As a buyer, I want to fill in a fact the Listing leaves out (no living area stated) so the figures stop resting on an assumption.
3. As a buyer, I want to see the agent's original value beside my correction, so I remember what I changed and why.
4. As a buyer, I want the model to know the agent misstated a fact, since that says something about the Listing's reliability.
5. As a buyer, when I re-capture the Listing and the agent has since changed the value, I want to be told, so I can decide whether my correction is still needed.
6. As a buyer, I want to write down what I learned at a viewing or from the neighbours and have the Oordeel weigh it.
7. As a buyer, I want the Oordeel to show as Achterhaald after I add a Correctie or change my Notitie.
8. As a buyer, I want both to be in the Markdown export.

## Decisions

1. **Two concepts.** Correction (structured, in the Case) and Note (free text, outside the Case). See ADR-0006.
2. **Correctable facts.** The Listing facts the Case computes with: `living_area`, `plot_area`, `construction_year`, `house_type`, `energy_label`, `ownership_situation`, `rooms`, `bedrooms`. This excludes Source facts, Observations and Findings: there the user re-fetches the Source or uploads a Document.
3. **Explanation required.** Every Correction carries a short explanation (e.g. "NEN 2580-meetrapport", "zelf nagemeten bij bezichtiging").
4. **Precedence.** A Correction outranks the Listing, the register (energielabel) and any Finding for the same fact. The original value and its provenance stay visible. An absent original shows as "onbekend".
5. **Fills gaps.** A Correction may supply a fact the Listing leaves out, with the same effect.
6. **Re-capture.** A new snapshot never removes a Correction. When the Listing's value differs from the value it had when the Correction was made, the Case marks the Correction and the UI says so. The user then keeps or removes it.
7. **Case, every profile.** Corrections belong to the house, are part of the Case and are the same for every Buyer Profile. A change makes the Verdict Achterhaald (cause `case`).
8. **Model sees both values.** Computations use the corrected value. The model's view of the Case shows the corrected value, the original and the explanation.
9. **Note.** One editable free text per house. The model reads and weighs it. It raises no Flag and never forces a Hard no. A change makes the Verdict Achterhaald (new cause `note`).
10. **Export.** Both are in the Markdown export, not kept private.
11. **UI.** A Correctie is made with a pencil beside the fact in the Dossier, which opens a small dialog with the value and the explanation. The Notitie is a text field on the Woning page, visible from both the Dossier and the Oordeel tab (e.g. under the Woning header). Layout follows `DESIGN.md`. A corrected fact is marked **gecorrigeerd**.

## Implementation Decisions

### Correction

- Storage: a `corrections` table per `funda_id` and fact key holding the value, the explanation, `created_at` and `listing_value_at_correction`. One live Correction per fact. Removing one deletes it.
- Case assembly: apply the Corrections to the snapshot before `build_case` derives anything, so every computation (comparables €/m², `asking_vs_comparables`, Expected Sale Price, Renovation Estimate, Flags, comparables matched by kind) reads the corrected value. A corrected soort woning also decides the kind (house or apartment) over funda's object type. The fact in `facts` gets provenance `correction` and carries `original` (value, provenance, fetch time and, for the register, the Source) and `explanation`. For the energielabel, the correction outranks the register; for the ownership situation, it outranks the erfpacht Finding. The Woningen list and the Woning header show corrected values too.
- Changed-since marker: `listing_changed: true` on the corrected fact when the current snapshot's value differs from `listing_value_at_correction`.
- Validation per key: positive integers for areas, rooms and bedrooms; a build year from 1100 to five years ahead; the energielabel from its known set and a soort woning funda uses (as `house_type.py` recognises it, not only the five categories).
- Verdict inputs: `built_from` gains the Corrections (key, value, explanation; not when they were made), and `changed_inputs` counts a change as `case`.
- Routes: `PUT /listings/{funda_id}/corrections/{key}`, `DELETE /listings/{funda_id}/corrections/{key}`, and `POST /listings/{funda_id}/corrections/{key}/keep` ("Correctie behouden": records the Listing's current value, so no Verdict input changes).

### Note

- Storage: one text per `funda_id`, with `updated_at`. An empty text means no Note.
- The Verdict prompt receives the Note as a separate, labelled input beside the Case. It is never in `facts` and never read by `flags`.
- Verdict inputs: `built_from.note_updated_at`. `changed_inputs` reports `note`, and the UI words it among the causes of Achterhaald. A deterministic Hard no never read the Note, so a Note change leaves it current.
- Route: `PUT /listings/{funda_id}/note`.
- `VERDICT_PROMPT_VERSION` bumps when the prompt changes.

## Out of scope

- A list of dated notes. One field is enough; the user can write dates in the text.
- Correcting Source facts, Observations or Findings.
- Turning a Note into Corrections automatically.
- The household's own renovation plans (`.scratch/own-renovation-plans/`).
