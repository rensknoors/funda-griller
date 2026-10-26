# 22: Export a Case and Verdict as Markdown for other LLMs

**What to build:** An **Exporteer als Markdown** download on a house: one `.md` file holding the Case and its current Verdict, written to be attached or pasted as context in another LLM chat. The file is generated deterministically from stored data (no LLM call), is in Dutch, and explains itself: what each section is and how much to trust each fact. The target LLM is unknown (possibly a free tier that trains on input), so the Buyer Profile part is always anonymised and can be left out.

**Blocked by:** 09 (Verdict and Bid Advice)

**Status:** ready-for-agent

### Endpoint and UI

- [x] `GET /api/listings/<id>/export.md?profile=true|false` (default `true`) returns `text/markdown` with a `Content-Disposition` filename from date and address (e.g. `2026-10-26-keizersgracht-12-amsterdam.md`)
- [x] UI: download button **Exporteer als Markdown** with a checkbox **Koperprofiel meesturen (geanonimiseerd)**, ticked by default, in the WoningHeader or Verdict area. Download only, no copy-to-clipboard
- [x] Single house only; no multi-house export from the comparison view

### Content (Dutch, sections in this order)

- [x] Preamble for the reading LLM: what Funda Griller is, what the file is for, that figures are decision support only, the provenance labels (Advertentie, Bron, Waarneming geschat, Bevinding door verkoper, Verouderd), and a bilingual legend of the glossary terms (Dossier = Case, Signaal = Flag, Oordeel = Verdict, Biedadvies = Bid Advice, …). No prepared questions at the end
- [x] Header: Case `built_from` versions, Verdict model and prompt version, export timestamp, whether the Koperprofiel is included
- [x] Woning: address, asking price, living and plot area, build year, energielabel, status, captured date, funda URL, and the full Listing description text
- [x] Facts grouped by provenance (Listing, Source, Observation, Finding) with Verouderd, geschat and door verkoper markers; Findings with their page references
- [x] Metrics: t.o.v. WOZ, t.o.v. vergelijkbaar, commute, affordability (only with the profile)
- [x] Each Comparable listed: address, asking price, m², price per m², sold or listed
- [x] Signalen with class, rule and evidence
- [ ] Verbouwingsraming once ticket 21 lands (classes, totals, items) (follow-up after 21 merges)
- [x] Oordeel: tier and reasoning of the current Verdict only, no history; Biedadvies: Openingsbod, Maximumbod, Voorwaarden, and the Maximumbod derivation (only with the profile)
- [x] With no Verdict, an Achterhaald Verdict or a Hard no, the export still works and says so plainly at the top
- [x] No photos or Document files embedded or linked (spec story 81)

### Anonymising (export only; the Gemini path is unchanged)

- [x] With the profile: the reduced Buyer Profile is included, always anonymised:
  - euro amounts derived from the household's finances (home equity, affordable maximum, monthly cost, the affordability limit in the derivation, and any such amount in Flag evidence) rounded to €5,000; monthly cost to €50
  - commute destination labels replaced by **Bestemming 1, 2, …**, keeping max minutes and computed travel time
  - household counts kept; Must-have, Nice-to-have and Deal-breaker texts kept verbatim
  - Openingsbod and Maximumbod stay exact; when affordability is the binding limit, the derivation says **begrensd door betaalbaarheid** without the exact affordable maximum
- [x] Without the profile (`profile=false`): no reduced Buyer Profile, no affordability figures, no Maximumbod derivation; Biedadvies keeps only Openingsbod, Maximumbod and Voorwaarden

### Tests

- [x] API tests: full Case with Verdict; no Verdict; Achterhaald Verdict; Hard no; with and without profile; raw income, asset balances, home address, commute addresses and commute labels never appear; exact home equity and exact affordable maximum never appear; affordability-bound Maximumbod shows "begrensd door betaalbaarheid"; no photo or Document URLs in the output

## Notes

- Built (2026-10-26): `GET /api/listings/<id>/export.md?profile=true|false` (`app/routes/export.py`) renders `app/export.py`, a pure module (added to the import-linter purity contract). Each section is one function in `SECTIONS`; the Verbouwingsraming is one more function after `flags` once ticket 21 lands. UI: **Exporteer als Markdown** link plus the **Koperprofiel meesturen (geanonimiseerd)** checkbox in the WoningHeader, so on both Dossier and Oordeel. Tests: `backend/tests/test_export_api.py`, `frontend/e2e/export.spec.ts`.
- Pending: Verbouwingsraming section, follow-up after ticket 21 merges. Status stays `ready-for-agent` until then.
- Decisions: Notices (no Verdict, Achterhaald, Hard no) are blockquotes right under the title. The Listing description sits in a fenced `text` block, verbatim, so its own Markdown cannot break the file's sections. Commute labels are replaced in Flag titles and in the Verdict's summary, reasoning and conditions too. Without the profile, Flags raised from the Buyer Profile (Must-have, Deal-breaker, commute limit, `headroom`) are left out and counted, since their titles carry the preference text; commute travel times stay, as Bestemming N without maximum. Kosten koper stays exact (it follows from the asking price). Comparables are listed without their funda URL.
- Known limit: the prompt version is the current `VERDICT_PROMPT_VERSION`; Verdicts do not store the version they were made with. Euro amounts the model may have written into its free-text reasoning are not rounded.
- Verified: backend `uv run pytest` and `lint-imports`, frontend `tsc --noEmit` and `npx playwright test` all pass.

## Comments

- Grilled (user, 2026-10-26): Dutch with a bilingual legend; Buyer Profile included by default but always anonymised, with a toggle to leave it out; download only; single house; full description included; current Verdict only; Comparables listed one by one; no question block.
