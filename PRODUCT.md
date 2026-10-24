# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack
Existing decision (spec, ADR-0002): Vite+, React and Base UI frontend with a custom design; Python (FastAPI, SQLite) backend over localhost. Runs locally with one command.

## Users
One person, a Dutch house hunter, on a desktop browser. Evaluates koopwoningen on funda one at a time, then compares candidates. Works at a desk with time to read; not a phone-at-viewing tool. Decides whether and how high to bid in a market where overbidding is normal.

## Product Purpose
Personal, local tool. Paste a funda URL; the app captures the Listing and builds a Case: a deterministic evidence file (Listing facts, Source facts, Observations from photos, Findings from seller Documents, affordability, Flags from versioned rules), each fact traceable to its origin. A Verdict (Must buy, Consider, Skip, Hard no) with Bid Advice (opening bid, Walk-away Maximum, conditions) follows. Success: the user trusts the evidence, sees at a glance which houses deserve a bid, and goes into bidding with defensible numbers.

## Positioning
Every fact shows where it came from and how far to trust it (official register, funda claim, model estimate, seller statement). The Case holds no judgement; only the Verdict judges, and a Hard no is applied by rule before any model runs. Generic portals and spreadsheets do not separate evidence from opinion this way.

## Operating Context
Single household, no accounts, no hosting. Buyer Profile (finances, preferences, deal-breakers) entered by hand and stored locally; only derived figures reach the LLM. Photos and Documents (Vragenlijst, Lijst van zaken, brochure) are shown only in the user's own UI. Data is refreshed only by manual refetch; old facts stay visible and are marked Stale. Sources can fail independently; the Case shows which succeeded, failed or were skipped. Four screens: Buyer Profile form, Listings list (doubles as comparison view), Case detail, Verdict page.

## Capabilities and Constraints
- Domain vocabulary fixed by GLOSSARY.md (Listing, Source, Stale, Case, Flag, Observation, Document, Finding, Verdict, Hard no, Bid Advice, Walk-away Maximum, Buyer Profile). UI copy uses these terms.
- UI copy is fully Dutch (confirmed). GLOSSARY terms are English identifiers: the Dutch UI labels for them are a copy decision still to be made in the briefs.
- Flags are classed pro, con, risk; Verdict has four tiers; provenance has four classes (Listing, Source, Observation, Finding).
- Photo-derived facts are marked as estimated; Findings as seller-stated with page reference.
- Desktop-first; narrow widths are secondary.
- Not advice: outputs are decision support, not legal, tax or mortgage advice.

## Evidence on Hand
Spec and tickets in `.scratch/funda-griller/`. Recorded pyfunda fixtures live on the `prototype/pyfunda-fetch` branch. No brand assets, logo or existing visual implementation.

## Product Principles
- Provenance is part of every fact, not a footnote.
- Evidence and judgement stay visibly separate: Case first, Verdict second.
- Scan first, drill down second: dozens of facts must stay readable, with rule and evidence one expand away.
- Nothing changes under the user: Stale is shown, never silently refreshed.
- Degrade honestly: missing or failed data is stated plainly, never papered over.

## Accessibility & Inclusion
No product-specific standard stated. Ticket 03 still requires accessible non-colour cues for provenance, Stale, Flags and Verdict tiers; use sensible web defaults (contrast, keyboard, focus, reduced motion).
