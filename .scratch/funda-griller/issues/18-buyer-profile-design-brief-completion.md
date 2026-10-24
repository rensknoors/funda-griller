# 18: Buyer Profile design-brief completion

**What to build:** Close the gaps between the shipped Koperprofiel form (ticket 05) and its brief in `design/screens.md`, section 1. Ticket 05 delivered a working, validated, versioned form; this ticket brings it to the full brief.

**Blocked by:** 06 (Case with affordability), for the Gevolgen panel's derived figures

**Status:** ready-for-agent

- [ ] Left sticky section index (a top select on narrow widths)
- [ ] Sticky **Gevolgen** panel with live derived figures (max hypotheek, overwaarde, budget) and the rules year, flagged `verouderd` when the table year is not the current year; empty hint "Vul inkomen in om je budget te zien"
- [ ] Inline validation on blur; save disabled while invalid, with the problem count and a jump link to the first problem
- [ ] Vak numbers are unique and sequential, including inside repeated rows
- [ ] Wensen rows (Must-have, Nice-to-have, Deal-breaker) can be reordered by keyboard
- [ ] Empty state (section 1 open, others collapsed with one-line hints), loading skeleton, and a save-failure banner with Opnieuw proberen
- [ ] After save, a diff summary ("Dit verandert N oordelen") linking to the list; depends on Verdicts existing, so this item may land after 09
- [ ] Self-hosted Source Sans 3 and the vak frame colour from `design/direction.md`
- [ ] Decide whether free-text Must-have, Deal-breaker and commute label values may reach the LLM verbatim (a user can type an address there); either constrain them or document the exception in the reduced-profile contract
