# 10: Design critique, audit and polish

**What to build:** With the v1 screens real, run the impeccable `critique`, `audit` and `polish` commands over them, fix what they find, and generate DESIGN.md from the shipped UI with `document`, so later tickets match the system. Re-run if the comparison view or later screens drift.

**Blocked by:** 09 (Verdict and Bid Advice)

**Status:** resolved

- [x] A UX critique of the four screens is recorded with the findings acted on
- [x] An audit covers accessibility (including non-colour cues for tiers, Flags and Stale), responsive behaviour and performance, and its issues are fixed
- [x] A polish pass is applied across the screens
- [x] DESIGN.md reflects the shipped UI (tokens, components, patterns)
- [x] The Playwright smoke test still passes

## Comments

### Critique (impeccable `critique`, dual-agent: design review + detector/browser evidence)

Run against the live app with fakes, at 1440 and 375 wide. Nielsen total **24/40 (Acceptable)**: status 2, real world 3, control 2, consistency 2, error prevention 3, recognition 2, efficiency 2, minimalism 3, error recovery 3, help 2. Design-specificity verdict: authored for this product (the vak, stamp and tier vocabulary is present), but thin in places. The figure strips and nested frames read generic. Several direction pieces were missing (herkomst legend, tier mark in the Dossier header, stamp Popovers, filter bar). Detector: 1 CLI finding (side-tab), plus in-browser cramped stamp padding, line length and long all-caps labels. The text-occlusion, repeated-text and section-index padding hits were false positives (content inside closed `<details>`).

| Finding | Severity | Done |
|---|---|---|
| A sold Woning shows no status on the Dossier or Oordeel, and the Oordeel still offers Biedadvies | P0 | Fixed. Status chip in the Dossier header; status banner on the Oordeel ("Deze woning is verkocht. Een biedadvies is niet meer van toepassing.", or an under-offer variant). The Status fact shows `Verkocht`/`Beschikbaar`, not the raw enum. New e2e `sold-woning.spec.ts`, written red first. |
| `.tier-glyph` redefined by the Oordeel styles, inflating list glyphs to 36px and rows to 49px | P1 | Fixed. Oordeel variants are scoped to `.tier-mark`; the list keeps the 18px glyph. |
| "Hoe berekend" lists two ceilings but never says which one bounds the Maximumbod | P1 | Fixed. A new line names the lowest ceiling and how far the Maximumbod sits under it. |
| Dossier lacks the herkomst legend and tier mark the direction asks for; fact groups hide their disclosure marker | P1 | Fixed. Legend of all stamp codes under the header; compact tier mark in the header; ▸/▾ marker on fact groups. |
| VRK stamp vermilion and dashed (direction: dotted; vermilion is reserved); VGL reused the 3DE glyph ◇ | P1 | Fixed. VRK is dotted form-blue; VGL is ⇄. |
| Risico Flag glyph is a square like Minpunt (direction: triangle) | P2 | Fixed. Vermilion triangle in Signalen and on Signaal chips. |
| Copy leaks: "1 feiten", "1 bevindingen", aria "1 risico's"; "Drempel: 0.5" English decimal; ▲/▼ missing on Dossier t.o.v. WOZ / vergelijkbaar | P2 | Fixed. `plural()` helper, nl-NL threshold, arrows on both figures. |
| Signaal chip text centres when wrapped; Documenten note ~130ch wide; stamps have no vertical padding | P3 | Fixed. |
| Focused Signaal used a 4px blue side stripe (detector side-tab) | P3 | Fixed. 1px form-blue outline plus the highlight wash. |

Deferred, recorded as follow-ups rather than fixed here:
- Dossier filter bar, sticky group index, global vak numbering and "Zie vak N" links for Source facts, stamp Popovers, Prijsverloop chart.
- URL routing / browser Back, and scroll restore from Oordeel back to Dossier.
- Voorwaarden derived from Risico Signalen (model prompt and backend).
- Koperprofiel on its own screen and a sticky Opslaan footer.
- Thousands grouping in money inputs.
- Per-Bron refetch on successful Bronnen stays: it is how Stale facts are refreshed, and the e2e covers it.
- The "API: reachable" line stays because the smoke test asserts it.
- Raw rule ids stay in the Signaal detail on purpose: the direction asks for rule id + version.
- Long 12px caps labels ("Adres eigen woning (blijft op dit apparaat)") stay as the deliberate vak label style.

### Audit (impeccable `audit`)

Before the fixes: **12/20 (Acceptable)**. Accessibility 2, Performance 3, Responsive 2, Theming 2, Implementation integrity 3. Implementation integrity verdict: pass; the system is coherent and product-specific, with the drift listed above.

| Finding | Severity | Done |
|---|---|---|
| Focus drops to `<body>` and `document.title` never changes on Woningen/Dossier/Oordeel switches | P1 (a11y) | Fixed. Focus moves to the screen heading (`tabIndex=-1`); the title is set per view. |
| Non-colour cues: tiers pass (fill/outline/dashed/hatch/double frame + glyph + word); Stale passes (hatch + bar + struck date + ⏲ + Verouderd); Flags only partly (risk square) | P2 | Fixed via the Risico triangle. Sold status is now a word chip, not only a struck address. |
| Hard-coded hatch, highlight and flash colours in 8 places | P2 (theming) | Fixed. `--hatch-light`, `--hatch-dark`, `--hatch`, `--highlight`, `--flash` tokens. Light only by design (direction: daylight desk scene). |
| Narrow Dossier: header actions stacked in a tall column; percentages wrapped mid-value in the list | P2 (responsive) | Fixed. Actions wrap in a row; `.num` is nowrap. |
| Small 12px buttons (~22px tall) on desktop | P3 | Kept. Desktop-first; narrow form controls already go to 44px. |
| Performance: photo thumbnails lazy-load, no layout thrash, one 200ms flash honouring reduced motion | n/a | Nothing to fix. |

A clean pass of `detect.mjs` over `frontend/src` after the fixes returned `[]`.

### Polish and DESIGN.md

The polish pass covered the items above plus a visual check of the Dossier, the Oordeel and the list at desktop and 375 wide. It also caught and fixed a regression from this pass (Bouwjaar briefly rendered as `1.931`). `DESIGN.md` at the repo root is generated from the shipped tokens and components. The impeccable `.impeccable/design.json` live-panel sidecar was not written; it is local tool state. Playwright: 24/24 pass, including the smoke test.
