# 32: VvE bijdrage and erfpachtcanon in the monthly costs

**What to build:** The net monthly cost (ticket 28) covers the mortgage only. For an apartment the VvE bijdrage, and on erfpacht the canon, add a real monthly cost the household pays. Carry both into the Case when known and show them as separate monthly lines next to the net mortgage cost, in the Dossier, the Oordeel and the export.

**Blocked by:** none

**Status:** needs-triage

### Current state

- No VvE fact: the funda kenmerk that holds the bijdrage was never captured. Its label could not be checked offline (stored snapshots keep no raw kenmerken); candidates are "Bijdrage VvE" and "Periodieke bijdrage" under the Vereniging van Eigenaren section.
- Erfpacht is known as a Listing fact (`ownership_situation`) and as a Finding (`finding.erfpacht`), but the canon is only in the Finding's free-text statement, never as an amount.

### Design

- **VvE:** read the bijdrage from the funda kenmerken by a configurable list of labels (like `listing_status_map`); verify the real label on the first live capture of an apartment and record it here. Parse "€ 150,00 per maand" to euros per month.
- **Erfpachtcanon:** the Findings extraction (`FINDINGS_INSTRUCTION`) asks for the canon as euros per year when the Document states it; stored on the Finding, quoted like the rest.
- **Monthly costs:** VvE and canon (per month) as separate lines beside net and gross mortgage cost; never folded into them, since a lender's norms do not count them.

### Acceptance criteria

- [ ] An apartment Listing with a VvE bijdrage carries it as a Listing fact in euros per month
- [ ] A Document stating an erfpachtcanon yields a Finding with the amount per year, page and quote
- [ ] The Dossier, Oordeel and export show VvE and canon per month beside the net mortgage cost, when known
- [ ] Verdict prompt names them; prompt version bumped

### Tests

- [ ] Provider: a pyfunda fixture with a VvE kenmerk is read into euros per month
- [ ] API: Findings with a canon amount; Case and export show the monthly lines

## Comments

Split from ticket 29 on 2026-11-09 at the user's request ("geen van beide" in this ticket).
