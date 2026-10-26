# 22: Export a Case and Verdict as Markdown for other LLMs

**What to build:** An **Exporteer als Markdown** download on a house: one `.md` file holding the Case and its current Verdict, written to be attached or pasted as context in another LLM chat. The file is generated deterministically from stored data (no LLM call), is in Dutch, and explains itself: what each section is and how much to trust each fact. The target LLM is unknown (possibly a free tier that trains on input), so the Buyer Profile part is always anonymised and can be left out.

**Blocked by:** 09 (Verdict and Bid Advice)

**Status:** ready-for-agent

### Endpoint and UI

- [ ] `GET /api/listings/<id>/export.md?profile=true|false` (default `true`) returns `text/markdown` with a `Content-Disposition` filename from date and address (e.g. `2026-10-26-keizersgracht-12-amsterdam.md`)
- [ ] UI: download button **Exporteer als Markdown** with a checkbox **Koperprofiel meesturen (geanonimiseerd)**, ticked by default, in the WoningHeader or Verdict area. Download only, no copy-to-clipboard
- [ ] Single house only; no multi-house export from the comparison view

### Content (Dutch, sections in this order)

- [ ] Preamble for the reading LLM: what Funda Griller is, what the file is for, that figures are decision support only, the provenance labels (Advertentie, Bron, Waarneming geschat, Bevinding door verkoper, Verouderd), and a bilingual legend of the glossary terms (Dossier = Case, Signaal = Flag, Oordeel = Verdict, Biedadvies = Bid Advice, …). No prepared questions at the end
- [ ] Header: Case `built_from` versions, Verdict model and prompt version, export timestamp, whether the Koperprofiel is included
- [ ] Woning: address, asking price, living and plot area, build year, energielabel, status, captured date, funda URL, and the full Listing description text
- [ ] Facts grouped by provenance (Listing, Source, Observation, Finding) with Verouderd, geschat and door verkoper markers; Findings with their page references
- [ ] Metrics: t.o.v. WOZ, t.o.v. vergelijkbaar, commute, affordability (only with the profile)
- [ ] Each Comparable listed: address, asking price, m², price per m², sold or listed
- [ ] Signalen with class, rule and evidence
- [ ] Verbouwingsraming once ticket 21 lands (classes, totals, items)
- [ ] Oordeel: tier and reasoning of the current Verdict only, no history; Biedadvies: Openingsbod, Maximumbod, Voorwaarden, and the Maximumbod derivation (only with the profile)
- [ ] With no Verdict, an Achterhaald Verdict or a Hard no, the export still works and says so plainly at the top
- [ ] No photos or Document files embedded or linked (spec story 81)

### Anonymising (export only; the Gemini path is unchanged)

- [ ] With the profile: the reduced Buyer Profile is included, always anonymised:
  - euro amounts derived from the household's finances (home equity, affordable maximum, monthly cost, the affordability limit in the derivation, and any such amount in Flag evidence) rounded to €5,000; monthly cost to €50
  - commute destination labels replaced by **Bestemming 1, 2, …**, keeping max minutes and computed travel time
  - household counts kept; Must-have, Nice-to-have and Deal-breaker texts kept verbatim
  - Openingsbod and Maximumbod stay exact; when affordability is the binding limit, the derivation says **begrensd door betaalbaarheid** without the exact affordable maximum
- [ ] Without the profile (`profile=false`): no reduced Buyer Profile, no affordability figures, no Maximumbod derivation; Biedadvies keeps only Openingsbod, Maximumbod and Voorwaarden

### Tests

- [ ] API tests: full Case with Verdict; no Verdict; Achterhaald Verdict; Hard no; with and without profile; raw income, asset balances, home address, commute addresses and commute labels never appear; exact home equity and exact affordable maximum never appear; affordability-bound Maximumbod shows "begrensd door betaalbaarheid"; no photo or Document URLs in the output

## Comments

- Grilled (user, 2026-10-26): Dutch with a bilingual legend; Buyer Profile included by default but always anonymised, with a toggle to leave it out; download only; single house; full description included; current Verdict only; Comparables listed one by one; no question block.
