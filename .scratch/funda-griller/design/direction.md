# Design direction: Het Formulier

Ticket 03. Decisions only, no production UI. Product truth lives in `/PRODUCT.md`. Per-screen briefs: `screens.md`.

Mode: **Operate** (all four screens). Build path: code-led (no image generation available). World chosen from the direction round (seed 37dc3057, assigned card, accepted as rolled).

## Thesis

Every fact is a numbered *vak* (box) on a Dutch government form, with its herkomst (provenance) stamped in a fixed margin beside it. The Case reads like an aanslagbiljet: dense, ruled, auditable. Refuses the SaaS card grid and dashboard-widget default.

## Scene (forces light theme)

One person at a desk in daylight, laptop or monitor, reading a long evidence file for 20+ minutes before a high-stakes bid. Light ground, ink-dark text, no glow.

## Own-world

Pale paper-grey ground, near-navy ink, one Rijks-blue for rules and primary action, one vermilion reserved for Hard no and risk. Hairline box borders at 1px. Square corners (radius 2px max). Boxed numbered fields. Tabular numerals everywhere money or area appears. Nothing decorative: if it is not a vak, a rule, a stamp, or a number, it is not there.

## Tokens (starting values, ticket 01/05 may tune)

| Role | Value |
|---|---|
| ground | `#f6f7f9` |
| surface (vak fill) | `#ffffff` |
| ink | `#0e1f3a` |
| ink-muted | `#4a5b73` (4.9:1 on ground) |
| rule | `#c3cad6` hairline, `#0e1f3a` for vak outer frame |
| form-blue | `#154273` (primary, links, focus ring, selected) |
| vermilion | `#c2410c` (Hard no, risk, destructive only) |
| stale-wash | repeating 45° hairline hatch over `#eef0f4` |

Colour strategy: Restrained. Accent never on inactive states.

## Type

One family, Source Sans 3 (workhorse UI sans, self-hosted, tabular figures via `font-variant-numeric: tabular-nums`). No display face.

Fixed rem scale, ratio ~1.15: 12 / 13 / 14 (base data) / 16 (body prose, reasoning) / 18 / 22 / 28 (price, tier). Labels 12px caps with 0.04em tracking. Vak numbers 11px semibold, form-blue. Prose (Verdict reasoning) capped at 68ch; data runs full width.

## Density

Default row 32px with 8px cell padding; "ruim" toggle gives 40px. Case detail targets 40+ visible facts at 1440x900 without scrolling inside groups. Gutters 16px; frame margin 24px.

## Layout grid

12-column, max 1440, desktop-first. Case detail uses a fixed **four-track fact row**: `nr (48) | label (240) | waarde (flex) | herkomst-kantlijn (280)`. The kantlijn never moves; only its contents change. Same track idea reused in the Listings table (fixed columns, row restyles on state, grid never breaks).

## Provenance system (four classes, non-colour first)

Each fact's kantlijn carries a stamp: glyph + 3-letter code + Dutch word + date. Border style encodes trust, ordered most to least trusted. Colour is secondary and the same blue for all four.

| Class | Code | Border | Glyph | Value treatment | Reads as |
|---|---|---|---|---|---|
| Source (register) | `BRN` | double rule | ◆ | plain | official |
| Listing | `ADV` | single solid | ■ | plain | stated by funda |
| Finding | `VRK` | dotted | ❝ | in quotes + `p. 7` page link | seller-stated, check original |
| Observation | `OBS` | dashed | ◔ | `≈` prefix, "geschat" | model estimate |

- Third-party Source (WOZ): own stamp `3DE` (derde partij), single solid border, glyph ◇ (open diamond), value prefixed `~`, word `onofficieel`. Never uses the double rule or ◆, so it cannot be read as official.
- Stamp is a Base UI Popover trigger: opens rule/bron detail, URL, fetch date, TTL.
- Each class also has a text legend pinned in the Case header so the code is learnable.

## Stale

Never colour-only. A Stale fact shows: the fetch date struck through with a clock glyph and the word **Verouderd**, the vak background switches to the hatch wash, and the row carries a left edge bar. The Listings list shows a count `3 verouderd` per row. Stale facts are never hidden or dimmed below 4.5:1.

## Flags (pro, con, risk)

Shape + word + position, not hue alone.

| Flag | Shape | Glyph | Word |
|---|---|---|---|
| pro | circle | + | Pluspunt |
| con | square | − | Minpunt |
| risk | triangle | ! | Risico (vermilion allowed as extra, never sole) |

Grouped in three labelled bands in that order on Case detail. Each Flag row expands (Base UI Collapsible) to rule id + version and the evidence facts, each evidence fact linking to its vak number (e.g. "Zie vak 14").

## Verdict tiers

Four tiers, each with fill pattern, glyph and label so they read in greyscale and at 20px.

| Tier | Mark | Treatment |
|---|---|---|
| Must buy | solid blue block, ✓ | filled |
| Consider | blue outline, ○ | outlined |
| Skip | grey outline, hatched fill, – | hatched |
| Hard no | vermilion double frame, ✕, diagonal bar | heavy frame, reason shown inline |

Tier order is the sort order. Hard no always shows its triggering deal-breaker beside the mark.

## Scanability of a big Case

1. Header strip: tier mark, price, asking vs WOZ, asking vs vergelijkbaar, headroom. Answerable in 3 seconds.
2. Flag bands next (Pluspunt, Minpunt, Risico); each shows title lines only, expand on demand.
3. Facts in named groups (Kenmerken, Prijs en waarde, Energie en milieu, Verkoper-informatie, Foto-waarnemingen, Documenten) as collapsible sections, each with a one-line summary and a count of Stale/estimated items.
4. Sticky group index on the left, fact filter bar: by herkomst class, `alleen verouderd`, `alleen geschat`.
5. Rows are one line; long values truncate with the full value on focus/hover and in the Popover.

## Comparison list at a glance

The Listings list *is* a table: fixed columns, one row per Listing, sorted by tier then price by default. Tier mark is the first column so rows scan as bands. Numeric columns right-aligned and tabular. Status change (e.g. beschikbaar to verkocht) restyles the row: struck address, status chip, lowered ink, grid unchanged.

## Motion

150 to 200 ms, state-only: expand/collapse, popover, row highlight on refetch. Respect `prefers-reduced-motion` (replace with instant). No page-load choreography.

## How Base UI primitives are themed

Base UI is unstyled; theme through CSS custom properties plus attribute selectors, no CSS-in-JS runtime assumed.

- Tokens in one `:root` layer; components style on `[data-checked]`, `[data-disabled]`, `[data-popup-open]`, `[data-invalid]`, `[data-open]`, `[data-highlighted]`.
- Mapping: Field + Input / NumberField render as boxed **vak** (label in caps above, hint below, number tag top-left). Select and Combobox share the vak frame. Checkbox and Switch are square, 2px radius, blue fill with ✓/bar glyph. Collapsible/Accordion for Flag and fact groups. Popover for provenance stamp. Tooltip only for truncated values (never the only access). Tabs for Case/Verdict switching. Dialog only for destructive confirms (archive, remove Document). Toast for refetch results.
- Focus ring: 2px form-blue offset 2px, always visible, 3:1 against adjacent colours.
- Hit targets 32px on desktop rows (above the WCAG 2.2 AA 24px minimum), 44px on narrow.
- One component vocabulary reused on all four screens; primary button = solid blue, secondary = outlined, destructive = vermilion outline.

## Accessibility (non-colour cues are mandatory per ticket)

- Every state carries glyph + word; colour is supplementary.
- 4.5:1 text contrast, 3:1 for UI and focus.
- Full keyboard path: table rows focusable with arrow keys, `Enter` opens, `x` toggles archive confirm.
- Tabular regions use real `<table>`/`role=grid` semantics; vak numbers are `aria-describedby` targets for Flag evidence links.
- Provenance stamp has an accessible name: "Bron: Energielabelregister, opgehaald 12 maart, verouderd".

## Narrow widths (desktop-first)

Below 1024: sticky group index becomes a top select; Listings table collapses columns by priority (tier, adres, vraagprijs stay; rest move into an expandable row). Below 720: fact row stacks, kantlijn drops *under* the value as a stamp line; Listings becomes a card list with tier mark on the left; Verdict is single column. Structure collapses, type does not scale.

## Copy (UI language: Dutch)

The confirmed Dutch label for every glossary term lives in `GLOSSARY.md` (`_Dutch UI_` line per term). Use those; do not invent variants. Two rules from that set: **Verouderd** is only for a Stale fact, **Achterhaald** is only for a Verdict or Case built on older inputs; **Woning** is the house in lists and navigation, **Advertentie** only where the captured snapshot is explicit.

## Open decisions

- Whether CSS is plain CSS modules or a utility layer (ticket 01 scaffold owns it).
- Font hosting: self-hosted Source Sans 3 assumed.
- No throwaway prototype was run: no screen stayed unresolved after the briefs (see end of `screens.md`).
