# 03: Design direction

**What to build:** The design foundation for all four screens (Buyer Profile form, Listings list, Case detail, Verdict page), produced with the impeccable skill: first `init` to capture durable product context, then `shape` for each screen. The surface is an Operate-mode tool, so scanability and trustworthy provenance matter more than decoration. Output is decisions and briefs, not production UI.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] Product context (users, mode, tone, constraints) is captured in PRODUCT.md
- [x] A shaped brief exists for each of the four screens covering information architecture, key states (empty, loading, error, Stale) and the main interactions
- [x] The visual direction is chosen and written down: type, colour, density, and how Base UI primitives will be themed
- [x] The brief shows how provenance (Listing, Source, Observation, Finding), Stale badges, Flags (pro, con, risk) and the four Verdict tiers are distinguished visually, including accessible non-colour cues
- [x] The brief shows how a Case with dozens of facts stays scannable, and how the comparison list reads at a glance
- [x] Any unresolved screen is settled with a throwaway prototype of UI variants, and the chosen variant is recorded
- [x] Desktop-first, with the briefs stating what changes at narrow widths

## Answer

Direction "Het Formulier" chosen. Product context: `PRODUCT.md`. Decisions: `.scratch/funda-griller/design/direction.md`. Screen briefs: `.scratch/funda-griller/design/screens.md`. No throwaway prototype run; fallback noted in screens.md. Dutch UI term set is proposed, not yet in `GLOSSARY.md` (open).
