# 18: Buyer Profile design-brief completion

**What to build:** Close the gaps between the shipped Koperprofiel form (ticket 05) and its brief in `design/screens.md`, section 1. Ticket 05 delivered a working, validated, versioned form; this ticket brings it to the full brief.

**Blocked by:** 06 (Case with affordability), for the Gevolgen panel's derived figures

**Status:** resolved

- [x] Left sticky section index (a top select on narrow widths)
- [x] Sticky **Gevolgen** panel with live derived figures (max hypotheek, overwaarde, budget) and the rules year, flagged `verouderd` when the table year is not the current year; empty hint "Vul inkomen in om je budget te zien"
- [x] Inline validation on blur; save disabled while invalid, with the problem count and a jump link to the first problem
- [x] Vak numbers are unique and sequential, including inside repeated rows
- [x] Wensen rows (Must-have, Nice-to-have, Deal-breaker) can be reordered by keyboard
- [x] Empty state (section 1 open, others collapsed with one-line hints), loading skeleton, and a save-failure banner with Opnieuw proberen
- [x] After save, a diff summary ("Dit verandert N oordelen") linking to the list; depends on Verdicts existing, so this item may land after 09
- [x] Self-hosted Source Sans 3 and the vak frame colour from `design/direction.md`
- [x] Decide whether free-text Must-have, Deal-breaker and commute label values may reach the LLM verbatim (a user can type an address there); either constrain them or document the exception in the reduced-profile contract

## Comments

- Done except the diff summary ("Dit verandert N oordelen"), which needs Verdicts: blocked by 09. Ticket stays open for that item only.
- Gevolgen: new `POST /api/buyer-profile/consequences` takes the finance vakken of a draft (blank balances count as zero, members without a birth date are left out) and returns max hypotheek (no energielabel bonus), overwaarde and budget (highest purchase price after kosten koper, starter exemption included), plus the rules year. Same arithmetic as the Case, so Case headroom = budget minus asking price (plus any label bonus).
- Old rules year is flagged **Achterhaald**, not `verouderd` as the brief says: GLOSSARY / CODING_STANDARDS reserve Verouderd for a Stale fact, and the Case (06) already uses Achterhaald for the same signal.
- Inline validation: `POST /api/buyer-profile/validation` checks a draft against the same model as save, without storing it. The form shows errors only for vakken that were blurred (or rejected on save), re-checks as you type, and disables Opslaan while any are shown.
- Free text to the LLM: decided to keep Must-have, Nice-to-have, Deal-breaker and commute labels verbatim (the LLM has to read the preference as written), documented as the exception in `reduce_profile`. They are constrained: a Dutch postcode or street-plus-number is rejected ("Geen adres of postcode: deze tekst gaat mee naar het taalmodel"), and the form says so beside those vakken. Best-effort pattern, not a guarantee.
- Font: `@fontsource-variable/source-sans-3`, bundled by Vite (no CDN). Vak frame `--vak-frame: #0e1f3a`.
- Reorder: Alt+↑/↓ in a Wensen row, or the ↑/↓ buttons.
- Closed with 09: after save the form reads `GET /api/verdicts/out-of-date` and says "Dit verandert N oordelen" (or "Er veranderen geen oordelen") with a link to the Woningen list; nothing re-runs by itself. The list refreshes on save so Hard no tiers follow the profile. Playwright in `e2e/verdict.spec.ts`.
