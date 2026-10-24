Status: ready-for-agent

# Funda Griller

## Problem Statement

Buying a house in the Netherlands means reading a funda Listing, then spending hours collecting everything the Listing doesn't say: energielabel, WOZ history, flood and soil risk, noise, nearby comparable prices, what the seller's Vragenlijst and Lijst van zaken reveal, and what the photos actually show. Then the household has to judge all of it against its own finances and wishes, and decide what to bid in a market where overbidding is normal. Doing this by hand for every candidate is slow, inconsistent between houses, and easy to get emotionally wrong. There is no single place that assembles the evidence, shows where each fact came from, and tells the household plainly whether the house deserves a bid and how high to go.

## Solution

A personal, local tool for one household. The user pastes a funda URL and the app fetches the Listing, downloads its photos, and builds a **Case**: a deterministic evidence file containing the Listing facts, facts from external Sources, Observations extracted from photos, Findings extracted from uploaded Documents, computed affordability, and Flags (pros, cons, risks) raised by versioned rules, each traceable to its evidence. The user can upload the seller's Documents (Vragenlijst, Lijst van zaken, anything else from the agent) and the Case rebuilds.

The Case contains no judgement. A deterministic Hard no is applied if the Case hits a deal-breaker from the **Buyer Profile**. Otherwise an LLM reads the Case plus a reduced Buyer Profile and returns a **Verdict** (Must buy, Consider, Skip, Hard no) with reasoning and **Bid Advice**: an opening bid, a **Walk-away Maximum**, and suggested conditions. Every fact shows its provenance and a **Stale** badge when old. Listings, Cases and Verdicts are stored so houses can be compared side by side.

## User Stories

### Buyer Profile

1. As a house hunter, I want to enter my household's income, household composition, assets and current home equity once, so that every Case is judged against my real situation.
2. As a house hunter, I want to enter my current home's value, outstanding mortgage and expected selling costs, so that the app knows how much equity I can bring to a purchase.
3. As a house hunter, I want to enter must-haves, nice-to-haves and deal-breakers, so that houses that can't work are filtered out and the rest are weighed against what I care about.
4. As a house hunter, I want to enter commute destinations, so that distance and travel time can be considered in Flags.
5. As a house hunter, I want to state my renovation tolerance (move-in ready versus project), so that the Verdict treats a dated kitchen or a poor energielabel appropriately.
6. As a house hunter, I want my Buyer Profile stored locally and never uploaded anywhere, so that my financial data stays private.
7. As a house hunter, I want to edit my Buyer Profile at any time and see Cases and Verdicts re-evaluate, so that I can explore "what if my income changes" or "what if I sell for more".
8. As a house hunter, I want the Buyer Profile form to validate obviously wrong input, so that a typo doesn't silently produce nonsense affordability.

### Capturing a Listing

9. As a house hunter, I want to paste a funda URL and have the Listing fetched, so that I don't copy facts by hand.
10. As a house hunter, I want the Listing's price, areas, rooms, build year, energielabel, coordinates, heating and description captured, so that the Case has the basics.
11. As a house hunter, I want all Listing photos downloaded and stored locally, so that they survive the listing being taken down and can be analysed.
12. As a house hunter, I want the Listing stored as a timestamped snapshot, so that I can see what it said when I looked, even after price changes or removal.
13. As a house hunter, I want the Listing's raw status string stored, so that "available", "under offer" and "sold" are preserved exactly as funda reported them.
14. As a house hunter, I want the asking-price history shown, so that I can see price drops and how long the house has been on the market.
15. As a house hunter, I want the funda brochure fetched and attached as a Document, so that I get the 30-page PDF analysed without downloading it myself.
16. As a house hunter, I want pasting the same URL twice to recognise the existing Listing and offer a re-fetch rather than create a duplicate, so that my list stays clean.
17. As a house hunter, I want a clear error when the Listing can't be fetched, so that I know whether it is a bad URL, a removed listing or the provider being blocked.
18. As a house hunter, I want a manual-entry form for a Listing, so that I can still build a Case if the fetch provider breaks.
19. As a house hunter, I want to upload my own photos when entering a Listing manually, so that Observations still work in the fallback path.
20. As a house hunter, I want the app to cope with missing floorplans, videos and 360 photos, so that a Listing without them still produces a full Case.

### Sources and the Case

21. As a house hunter, I want the energielabel looked up from the official register, so that I'm not relying on what the Listing claims.
22. As a house hunter, I want WOZ values over time shown, so that I can compare the asking price to the tax valuation.
23. As a house hunter, I want WOZ marked as coming from an unofficial third-party source, so that I know how far to trust it.
24. As a house hunter, I want flood and soil risk for the address, so that I'm aware of environmental risks the Listing doesn't mention.
25. As a house hunter, I want noise levels for the address, so that I know about a busy road or railway before viewing.
26. As a house hunter, I want nearby comparable listings and sold prices, so that I can see whether the ask is in line with the neighbourhood.
27. As a house hunter, I want the asking price compared to WOZ and to comparables as computed metrics, so that overpricing is quantified, not just felt.
28. As a house hunter, I want each Source fact to carry its fetch date, so that I can tell how current it is.
29. As a house hunter, I want facts older than their Source's time-to-live marked Stale, so that I don't unknowingly rely on old data.
30. As a house hunter, I want to manually refetch a Listing or Source, so that I decide when to refresh and spend the calls.
31. As a house hunter, I want stale facts to stay visible and not vanish or auto-refresh, so that the Case never changes under me without my action.
32. As a house hunter, I want one Source failing to degrade the Case gracefully, so that a down register doesn't block the whole Case.
33. As a house hunter, I want the Case to say which Sources succeeded, failed or were skipped, so that I know what the Case is missing.

### Provenance

34. As a house hunter, I want every fact labelled by provenance (Listing, Source, Observation, Finding), so that I know what's official, what's a claim and what's an estimate.
35. As a house hunter, I want photo-derived facts clearly marked as estimated, so that I don't mistake a model's guess for an inspection result.
36. As a house hunter, I want seller-stated Findings clearly marked as such with their page reference, so that I can check the original.

### Photo Observations

37. As a house hunter, I want photos analysed once at ingestion for condition signals (kitchen and bathroom age, damp or mould, roof and facade state, renovation level), so that visual risks reach the Case.
38. As a house hunter, I want each Observation to cite the photo(s) it came from, so that I can check it myself.
39. As a house hunter, I want Observations stored and reused, so that the Case is reproducible and I'm not charged to re-analyse unchanged photos.
40. As a house hunter, I want to re-run photo analysis on demand, so that I can pick up a better model later.

### Documents

41. As a house hunter, I want to upload the Vragenlijst, Lijst van zaken and other seller or agent PDFs against a Listing, so that what the seller disclosed informs the Case.
42. As a house hunter, I want Findings extracted from each Document (for example asbestos, leaks, leased solar panels, erfpacht, subsidies, what stays and what doesn't), so that I don't read every page myself.
43. As a house hunter, I want each Finding to carry its page reference, so that I can verify it in the original.
44. As a house hunter, I want Findings to feed Flags like any other fact, so that a disclosed problem shows up in the cons and risks.
45. As a house hunter, I want to re-upload or remove a Document and have the Case rebuild, so that corrections are reflected.
46. As a house hunter, I want a Document that couldn't be read to be reported plainly, so that I don't assume it was analysed.
47. As a house hunter, I want Documents stored locally and kept private, so that seller papers don't leave my machine except to be analysed.

### Affordability

48. As a house hunter, I want my maximum mortgage computed from income and current Dutch rules, so that I know my real ceiling.
49. As a house hunter, I want kosten koper computed (transfer tax, notary, valuation, advice), so that the true cost of a bid is visible.
50. As a house hunter, I want the equity from selling my current home included, so that the overall budget is realistic.
51. As a house hunter, I want estimated monthly costs at the asking price and at my Walk-away Maximum, so that I can see what each means for my budget.
52. As a house hunter, I want the headroom above the asking price shown, so that I know how much overbidding I can absorb.
53. As a house hunter, I want the rules version and year used for affordability shown, so that I know what assumptions the numbers rest on.
54. As a house hunter, I want the energielabel's effect on borrowing capacity and on likely renovation cost included, so that a poor label is priced in.

### Flags

55. As a house hunter, I want pros, cons and risks listed as Flags, so that I can scan what matters about a house.
56. As a house hunter, I want each Flag to show the rule that raised it and the facts behind it, so that I can trust or challenge it.
57. As a house hunter, I want Flag thresholds to depend on my Buyer Profile where relevant, so that "too expensive" and "too far" mean what they mean for me.
58. As a house hunter, I want Flags grouped by pro, con and risk, so that the Case detail reads quickly.
59. As a house hunter, I want asking price far above WOZ or comparables raised as a Flag, so that overpricing doesn't pass unnoticed.
60. As a house hunter, I want a deal-breaker hit to be displayed as the reason for a Hard no, so that it's obvious why a house was ruled out.
61. As a developer of this tool, I want Flag rules declarative and versioned, so that adding or tuning a rule doesn't mean changing application flow.

### Verdict and Bid Advice

62. As a house hunter, I want a Verdict tier (Must buy, Consider, Skip, Hard no) for each Case, so that I get a clear first answer.
63. As a house hunter, I want the Verdict's reasoning written in plain language that cites Flags and facts, so that I can see why.
64. As a house hunter, I want a Hard no applied deterministically when a deal-breaker is hit, so that the LLM can never talk me into a house that violates my own rules.
65. As a house hunter, I want an opening bid and a Walk-away Maximum, so that I go into a bidding round with numbers.
66. As a house hunter, I want the Walk-away Maximum to be derived from comparables and my affordability, not invented, so that it is defensible.
67. As a house hunter, I want suggested conditions (financing clause, building inspection, specific Document follow-ups), so that I protect myself in the offer.
68. As a house hunter, I want the Verdict to know each fact's provenance, so that a seller's claim is weighed below an official register.
69. As a house hunter, I want Verdicts versioned against the Case and Buyer Profile that produced them, so that I can see how a change in my situation changed the answer.
70. As a house hunter, I want to re-run a Verdict on demand, so that I can regenerate after uploading a Document or editing my profile.

### Listings list and comparison

71. As a house hunter, I want a list of all captured Listings with Verdict tier, price, area and key metrics, so that I can compare candidates side by side.
72. As a house hunter, I want to sort and filter the list by tier and price, so that I focus on the best candidates.
73. As a house hunter, I want to see at a glance which Listings have Stale data, so that I know which to refetch.
74. As a house hunter, I want to archive a Listing I've dropped, so that the list stays relevant without losing history.
75. As a house hunter, I want to see a Listing's status change (for example available to sold) after a refetch, so that I know when a house is no longer in play.

### Privacy and operation

76. As a house hunter, I want only derived financial figures sent to the LLM, never raw income or asset balances, so that my finances stay private.
77. As a house hunter, I want photos and Documents sent to the LLM only for extraction, so that the one unavoidable disclosure is limited and understood.
78. As a house hunter, I want the app to run locally with one command and no account, so that setup is trivial.
79. As a house hunter, I want API keys and model names kept in configuration, so that I can swap models or keys without code changes.
80. As a house hunter, I want the app to never crawl, bulk-fetch or run searches on funda, so that usage stays user-initiated and low-volume.
81. As a house hunter, I want photos and Documents shown only in my own UI and never re-served elsewhere, so that I don't republish other parties' material.

### Quality

82. As a developer of this tool, I want a regression set of 5–10 Listings with my expected tier, so that prompt or rule changes can be checked against my own judgement.
83. As a developer of this tool, I want that regression run on demand against the real model, not in the normal test run, so that routine tests stay fast, free and deterministic.
84. As a developer of this tool, I want all external access (funda, Sources, Gemini) behind replaceable adapters, so that tests run offline and a broken provider can be swapped.

## Implementation Decisions

**Shape.** A Python backend (FastAPI, SQLite) and a Vite+, React and Base UI frontend with a custom design, talking over localhost. Runs locally with one command; no deployment, no auth, single household. See ADR-0001 (Case is deterministic, only the Verdict judges) and ADR-0002 (ingest via pyfunda).

**Domain vocabulary** is fixed by `GLOSSARY.md`: Listing, Source, Case, Flag, Observation, Document, Finding, Stale, Verdict, Hard no, Bid Advice, Walk-away Maximum, Buyer Profile. Code, UI copy and tickets use these terms.

**Pipeline.**
1. Listing provider fetches the Listing by URL and returns a normalised Listing plus photo URLs, price history and a brochure URL.
2. Photos and brochure are downloaded and stored locally per Listing snapshot.
3. Vision model extracts Observations from photos once; results are cached against the photo set.
4. Documents uploaded by the user, plus the funda brochure, are read by the model to extract Findings with page references; results are cached against the Document.
5. Source clients fetch Source facts (energielabel, WOZ, flood and soil risk, noise, comparables), each stored with a fetch date and time-to-live.
6. The Case is assembled deterministically: facts with provenance, computed metrics (asking vs WOZ, asking vs comparables), affordability, and Flags from rules.
7. Deal-breaker check: a hit forces Hard no and skips the LLM.
8. Otherwise the Verdict model receives the Case plus the reduced Buyer Profile and returns a tier, reasoning and Bid Advice.

**Modules (deep, small interfaces).**
- *Listing provider*: one port, `fetch(url) -> Listing`. Adapters: pyfunda (production), manual entry (fallback). Parsing is defensive because attribute names differ between listings and the API is undocumented.
- *Source client*: one port per Source, each returning facts with a fetch date. Failure of one Source never fails the Case; the Case records succeeded, failed and skipped Sources.
- *LLM client*: one port covering photo Observations, Document Findings and the Verdict; Gemini in production. Model IDs for the vision and Verdict roles live in configuration and are swappable. The real model identifiers must be confirmed against Google's documentation at build time.
- *Case builder*: pure assembly of facts, metrics, affordability and Flags; no I/O, no judgement.
- *Flag rules*: declarative, versioned rule set; each Flag records the rule id, version and evidence facts. Thresholds may reference derived Buyer Profile values.
- *Affordability engine*: max mortgage, kosten koper, equity, monthly cost, bidding headroom, using Dutch rules for a stated year, which is recorded on the output.
- *Verdict service*: applies the deterministic Hard no, builds the reduced prompt input, calls the LLM client, and validates that the response is one of the four tiers and a coherent Bid Advice.
- *Store*: SQLite persistence for Buyer Profile, Listing snapshots, photos and Documents (files on disk, rows in DB), Observations, Findings, Source facts, Cases, Verdicts.

**Data model essentials.**
- A Listing snapshot is immutable and timestamped. A Listing is keyed on the funda id from the URL; the provider's internal id is stored too, because the two differ.
- The raw status string is stored verbatim on the snapshot.
- Every fact in a Case has a provenance class (Listing, Source, Observation, Finding), a fetch or extraction timestamp, and for Observations and Findings a reference to its photo or page. Staleness is computed from the timestamp and the Source's time-to-live, not stored.
- Cases and Verdicts are versioned against the snapshot, rule version, Buyer Profile version and model identifiers that produced them.

**API contract (high level).**
- Buyer Profile: read and update.
- Listings: create from URL, list, read, refetch, archive.
- Documents: upload, list, remove, per Listing.
- Case: read the current Case for a Listing.
- Verdict: read, and request a re-run.
Errors for fetch failures distinguish bad URL, removed listing and provider blocked.

**Privacy rules.**
- Only the Case and a reduced Buyer Profile (derived affordability figures plus preferences, never raw income, balances or address) reach the Verdict model. A paid-tier Gemini key is required; the current terms should be checked at setup.
- Photos and Documents are sent in full for extraction only.
- Photos and Documents are stored locally and displayed only in the user's own UI.

**Ingestion constraints (from the pyfunda prototype).**
- The provider must never call `search()`: it returns 401 from the mobile API and silently falls back to scraping.
- Pin `tls-client` below 2.0, which breaks pyfunda 3.1.5 on import.
- pyfunda is AGPL-3.0: acceptable for local personal use; revisit before any hosting or sharing.
- Attribute paths varied between the two tested listings; parse defensively.
- Floorplans, video and 360 photos were empty on both tested listings; treat all three as optional.
- The brochure download needs a browser user agent (403 without).
- WOZ history comes from a third-party service, not funda or an official register, and is labelled accordingly.
- `similar_listings()` returns IDs only; comparables need a follow-up fetch per ID, kept to a small, user-triggered number.
- The snapshot serialiser must handle the provider's dataclass objects (a naive dump produced empty output).

**UI.** Four screens: Buyer Profile form; Listings list that doubles as the comparison view; Case detail (Flags grouped as pros, cons, risks, each expandable to rule and evidence, provenance beside every fact, Stale badges, Documents panel); Verdict page with Bid Advice. Custom visual design on Base UI primitives.

**v1 tracer bullet.** Profile entry, URL in, pyfunda fetch and snapshot, Case from Listing plus energielabel plus WOZ plus affordability, a handful of Flag rules, deterministic Hard no, Verdict and Bid Advice, minimal UI across the four screens. Photos and Observations, Documents and Findings, the remaining Sources, comparison polish and the regression set widen it afterwards; the structure above must allow each to be added without reshaping the Case.

## Testing Decisions

**What a good test is.** It exercises behaviour through the public seam and asserts on observable results (the Case content, Flags, tier, Bid Advice, stored data), not on internal functions, prompt wording or rule implementation. Refactoring the Case builder, rules or affordability must not break tests.

**Primary seam: the backend HTTP API.** Tests drive the FastAPI app: save a Buyer Profile, post a URL, upload a Document, then read the Case, Verdict and Listing list. Real SQLite on a temporary file. This covers ingestion, Case assembly, Flags, affordability, Hard no capping and persistence in one place.

**Fakes only at the outside edge.** Three ports, each with a test double:
- Listing provider, using fixtures recorded from the two prototype listings (one sold, one live).
- Source clients, using fixtures.
- LLM client, returning canned Observations, Findings and Verdicts.
Tests never contact funda, any register, or Gemini.

**Cases to cover through the API:** a normal live Listing end to end; a Listing with no floorplan or video; a sold Listing (status preserved); duplicate URL; fetch failure kinds; one Source failing while the Case still builds; Stale marking after the time-to-live passes with a controllable clock; a deal-breaker forcing Hard no with the LLM client never called; the reduced Buyer Profile sent to the LLM contains no raw income or asset values; profile change producing a new Verdict version; Document upload producing Findings that raise a Flag; re-upload rebuilding the Case.

**Secondary seam: the Verdict regression set.** 5–10 Listings with the user's expected tiers, run against the real Gemini model on demand only. It is not part of the normal test run because it's slow, costs money and is non-deterministic. Its purpose is to gate prompt and rule changes.

**UI.** One Playwright smoke test against the API with fakes confirms the four screens render a Case with Flags, provenance and a Verdict. No component-level tests in v1.

**Not tested directly.** Affordability arithmetic and individual Flag rules, which are covered through the API with fixture Buyer Profiles. If the affordability tables become dense, a direct pure-function seam can be added later.

**Prior art.** None; the repo is greenfield. The recorded fixtures from the pyfunda prototype under the prototype branch are the starting point for provider fixtures.

## Out of Scope

- Multiple users, accounts, auth, sharing, hosting or deployment.
- Any funda search, crawling, alerts or bulk operations; only user-initiated single-URL fetches.
- Rentals, other portals (Pararius and the like) and other countries.
- Browser extension or browser-side capture (a possible future adapter behind the Listing provider port).
- Bank or government integrations (Mijn Overheid, bank accounts); the Buyer Profile is entered by hand.
- Paid Kadaster transaction data.
- Neighbourhood statistics (CBS), school quality, and parsing of VvE financial documents (later).
- Automatic refresh of Stale data.
- Legal, tax or mortgage advice; outputs are decision support only.
- Republishing, re-serving or sharing photos and Documents.

## Further Notes

- Open risks (first three addressed under Resolved risks below; ticket 02): the raw status string funda returns for "under offer"; whether erfpacht appears in the Kadaster items; the real Gemini model identifiers; the comparables Source being thin without paid Kadaster data.

### Resolved risks (ticket 02, 2026-10-24)

- **Under-offer status string: unobtainable from a real listing for now.** `search()` returns 401 so under-offer Listings cannot be discovered, and no known under-offer URL was available, so the string is not verified live. pyfunda 3.1.5 reads the raw status from the detail `Status` item or `advertising.status` and normalises `Beschikbaar`/`available` to `available`, `Onder bod`/`negotiations` to `negotiations`, `Verkocht`/`sold`/`unavailable` to `sold`, and passes any other string through unchanged. Observed live: `Beschikbaar` (available) and `Verkocht` (sold). Expect `Onder bod` for under offer; "sold subject to contract" (onder voorbehoud) has no mapping and is unknown. Decision: store `raw_status` verbatim (already required), map via the `[listing_status_map]` table in `config/defaults.toml`, and treat any unmapped string as "unknown, shown raw" rather than failing. Capture the real string the first time an under-offer Listing is fetched and add it to the table and the fixtures.
- **Erfpacht: field located, erfpacht value and description not checked.** Kadaster data arrives in the detail `KenmerkSections` entry titled `Kadastrale gegevens`: an item `cadastral-parcel` (label is the parcel, e.g. `RAALTE O 988`) with children `cadastral-area` (`Oppervlakte`) and `cadastral-ownershipsituation` (label `Eigendomssituatie`, value `Volle eigendom` on both tested Listings). Erfpacht should therefore appear as a different `Eigendomssituatie` value, not a separate field; the exact erfpacht wording (and canon/einddatum, which are probably only in the description or Documents) was not seen. Decision: the Listing adapter reads `Eigendomssituatie` by item id, stores it verbatim, and raises a risk Flag for any value other than `Volle eigendom`; the description and Documents (Findings) remain the source for canon and term. The Flag rule must match on "not Volle eigendom", not on the word erfpacht.
- **Gemini model identifiers: resolved against ai.google.dev/gemini-api/docs/models (fetched 2026-10-24).** Current stable: `gemini-4-argon` (flagship reasoning), `gemini-3.8-flash` (most capable Flash), `gemini-3.6-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`. Preview: `gemini-3-flash-preview`, `gemini-3.1-pro-preview`. `gemini-2.5-*` still served but limited to existing users; `gemini-2.0-flash*` and `gemini-3-pro-preview` are shut down. The models page does not list input modalities, so image and PDF input must be confirmed on the model's own page at build time. The user chose `gemini-3.8-flash` for both roles; defaults: vision role and Verdict role both `gemini-3.8-flash`. Both are configuration, swappable per the existing requirement.
- **Gemini paid-tier data use (ai.google.dev/gemini-api/terms, fetched 2026-10-24).** Under Paid Services Google does not use prompts or responses to improve its products and the terms do not mention human review; unpaid services do use content for improvement and allow human review, and the terms say not to submit sensitive or personal information to them. Google logs paid prompts and responses for a limited, unspecified period solely to detect Prohibited Use Policy violations and meet legal disclosure duties, and data may be stored transiently or cached in any country where Google operates. AI Studio counts as paid if the Cloud project has active billing; in the EEA, Switzerland and the UK the paid terms apply to all services. Consequence: a billed key is required (as already stated), photos and Documents are still sent in full, and the reduced Buyer Profile rule stays; re-check the terms at setup.
- **Comparables thin without paid Kadaster data:** not in scope for this ticket; remains open and belongs to ticket 14.
- pyfunda uses an undocumented, reverse-engineered mobile API and may break at any time; the manual-entry fallback exists for that reason (ADR-0002).
- The prototype is preserved on the `prototype/pyfunda-fetch` branch, with findings in its result file; it is a primary source for the provider adapter and its fixtures.
- Dutch affordability rules (leennormen, NHG limits, overdrachtsbelasting exemptions) change yearly; the engine should be data-driven by year so updates are table changes.
