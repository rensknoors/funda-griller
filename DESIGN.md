---
name: Funda Griller
description: A local evidence file and verdict for Dutch koopwoningen, set on a Total Design raster under a committed cobalt band.
colors:
  ground: "#ffffff"
  band: "#eef2fb"
  band-strong: "#dde5f7"
  line: "#e1e6f0"
  line-strong: "#c2cbdd"
  ink: "#0f1830"
  ink-hover: "#253151"
  ink-2: "#465270"
  ink-3: "#66718c"
  cobalt: "#1f4fd1"
  cobalt-hover: "#173ea8"
  cobalt-tint: "#e4ebfd"
  cobalt-halo: "#cddafa"
  hero: "#1a44c2"
  hero-raised: "#2452d6"
  on-hero-2: "#c9d7fc"
  green: "#0a6f45"
  green-tint: "#e3f3ea"
  ochre: "#9a5800"
  ochre-fill: "#a85f00"
  ochre-tint: "#fdf1dc"
  vermilion: "#c2410c"
  vermilion-tint: "#fdeee6"
  vermilion-line: "#e6b39b"
  violet: "#5b3fb0"
  violet-line: "#a99ad8"
typography:
  display:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "56px"
    fontWeight: 750
    lineHeight: 1
    letterSpacing: "-0.025em"
    fontVariation: "'wdth' 78"
  headline:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "40px"
    fontWeight: 750
    lineHeight: 1.05
    letterSpacing: "-0.02em"
    fontVariation: "'wdth' 80"
  figure-large:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "48px"
    fontWeight: 750
    lineHeight: 1.05
    letterSpacing: "-0.02em"
    fontFeature: "'tnum'"
    fontVariation: "'wdth' 80"
  figure:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "24px"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-0.015em"
    fontFeature: "'tnum'"
  title:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "20px"
    fontWeight: 650
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "'tnum'"
  prose:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.4
rounded:
  band: "4px"
  control: "6px"
  dialog: "8px"
  pill: "999px"
spacing:
  xxs: "4px"
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  xxl: "40px"
  rail-gap: "56px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.ground}"
    rounded: "{rounded.control}"
    padding: "0 14px"
    height: "38px"
  button-primary-hover:
    backgroundColor: "{colors.ink-hover}"
  button-secondary:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "0 14px"
    height: "38px"
  button-secondary-hover:
    backgroundColor: "{colors.band}"
  button-link:
    textColor: "{colors.cobalt}"
  button-destructive:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.vermilion}"
    rounded: "{rounded.control}"
  input:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "8px 10px"
    height: "40px"
  hero-band:
    backgroundColor: "{colors.hero}"
    textColor: "{colors.ground}"
    padding: "40px 0 36px"
  capture-panel:
    backgroundColor: "{colors.hero-raised}"
    textColor: "{colors.ground}"
    rounded: "{rounded.band}"
    padding: "18px 20px 20px"
  tier-pill-must-buy:
    backgroundColor: "{colors.green-tint}"
    textColor: "{colors.green}"
    rounded: "{rounded.pill}"
    height: "28px"
  tier-pill-consider:
    backgroundColor: "{colors.ochre-tint}"
    textColor: "{colors.ochre}"
    rounded: "{rounded.pill}"
    height: "28px"
  tier-pill-hard-no:
    backgroundColor: "{colors.vermilion-tint}"
    textColor: "{colors.vermilion}"
    rounded: "{rounded.pill}"
    height: "28px"
  tier-band-consider:
    backgroundColor: "{colors.ochre-fill}"
    textColor: "{colors.ground}"
    rounded: "{rounded.band}"
    padding: "36px 40px"
  tier-band-must-buy:
    backgroundColor: "{colors.green}"
    textColor: "{colors.ground}"
    rounded: "{rounded.band}"
    padding: "36px 40px"
  stamp:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.control}"
    padding: "2px 8px"
  stamp-finding:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ochre}"
    rounded: "{rounded.control}"
    padding: "1px 7px"
  stamp-observation:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.violet}"
    rounded: "{rounded.control}"
    padding: "2px 8px"
  weak-grounding:
    backgroundColor: "{colors.ochre-tint}"
    textColor: "{colors.ochre}"
    rounded: "{rounded.control}"
    padding: "8px 10px"
  chip:
    backgroundColor: "{colors.band}"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.pill}"
    height: "22px"
---

# Design System: Funda Griller

## Overview

**Creative North Star: "The Total Design Raster"**

A white sheet ruled by a Crouwel-style grid, capped by one committed field of cobalt. The top bar and a full-bleed hero band in deep cobalt form a single region at the top of every screen: it carries the page title and lede, the screen's first task (the Woningen capture field, the woning header with its Dossier/Oordeel tabs, the Koperprofiel title), and nothing else. Below it, hierarchy comes from scale, weight and whitespace, never from frames: one column of sections divided by hairlines, with cobalt-tinted bands laid under the few things that need grouping (key figures, bid figures, Gevolgen, empty states). Archivo, a grotesk with a width axis, does the heavy lifting: condensed and very bold for titles and money, normal width for reading. Numbers are tabular everywhere, because the product is a comparison of figures.

The density is an analyst's, not a dashboard's: an airy comparison table, a dossier of fact rows in fixed tracks so the herkomst stamps line up, and an Oordeel where the tier takes a whole coloured band. Colour is committed at the top and semantic below. Cobalt owns the region and still marks links, selection and focus; ink carries the type and the primary action; green, ochre and vermilion form a three-step scale of favourable, caution and risk that runs through tiers, flags, stamps and the figures themselves.

Frames appear only where a border carries meaning. A herkomst stamp's border style says how far to trust a fact; the Harde afwijzing wears a double vermilion rule. Everything else is open. The boxed form and the SaaS card grid are the rejected alternatives.

**Key Characteristics:**
- Deep cobalt (#1a44c2) top bar and full-bleed hero band as one region on every screen; white below.
- Neutrals tinted toward cobalt: bands #eef2fb, hairlines #e1e6f0, ink #0f1830; no cards.
- Archivo variable, condensed (wdth 78 to 88) and heavy (650 to 750) for titles and figures; tabular numerals globally.
- Ink primary buttons, even on cobalt; cobalt for the region, links, selection and focus.
- Green favourable, ochre caution, vermilion risk: on tiers, flags, stamps and directional figures.
- Every coloured state also has a shape, icon or sign and a Dutch word.
- Herkomst encoded by border style: double, solid, dotted, dashed, filled band.
- Stale and Achterhaald shown as a diagonal hatch, never as colour alone.

## Colors

A committed cobalt region over a cobalt-tinted white sheet, with a three-step semantic scale (green, ochre, vermilion) below it.

### Primary
- **Hero Cobalt** (#1a44c2): the top bar and the full-bleed `.hero` band, one continuous region. Text on it is white, secondary text **Hero Mist** (#c9d7fc); the bar's bottom hairline is white at 22%. The focus outline turns white inside it, and selection inverts to white with cobalt text.
- **Hero Raised** (#2452d6): panels set on the hero, chiefly the Woningen capture field, and the stepper hover fill.
- **Cobalt** (#1f4fd1): links, link-buttons, "Hoe berekend" disclosures, `accent-color` and caret, the focus outline on white, the Register stamp's double border, and a 3px top rule on the key-figures and Biedadvies bands. Hover darkens to **Cobalt Hover** (#173ea8).
- **Cobalt Tint** (#e4ebfd): row flash after capture, the targeted-fact highlight, a focused flag.
- **Cobalt Halo** (#cddafa): text selection on white and the 3px input focus ring.
- **Ink** (#0f1830): all headings and values below the hero, primary buttons (including the Ophalen button on the capture panel), the checked tier-toggle ring, the Verkocht chip, the lower half of the wordmark. Ink buttons hover to **Ink Hover** (#253151).

### Secondary
- **Woud Green** (#0a6f45) and **Green Tint** (#e3f3ea): the Zeker kopen tier (pill, full band), pro flags, a successful source, and the favourable figure tone.

### Tertiary
- **Ochre** (#9a5800), **Ochre Fill** (#a85f00) and **Ochre Tint** (#fdf1dc): caution. The Overwegen pill (tint ground, ochre ring glyph and text) and the full Overwegen band on the Oordeel (ochre fill, white text); minpunt flags (square tint glyph, ochre heading); the Verkoper stamp's dotted border; weak-grounding notes under a bid; the concern figure tone.
- **Vermilion** (#c2410c), **Vermilion Tint** (#fdeee6) and **Vermilion Line** (#e6b39b): risk flags, error notices and banners (a filled vermilion notice on the hero), invalid inputs, destructive buttons, the Harde afwijzing pill, block and band, failed sources, and the shortfall figure tone.
- **Violet** (#5b3fb0) with **Violet Line** (#a99ad8): the Foto's observation stamp only, text and dashed border.

### Neutral
- **Ground** (#ffffff): page below the hero, inputs, secondary buttons, stamps, hero text.
- **Band** (#eef2fb): grouping bands, hover fills, empty states, the computed stamp, chips.
- **Band Strong** (#dde5f7): pressed buttons, energy-label badge, skeleton shimmer peak, Onder bod chip.
- **Line** (#e1e6f0): section and row hairlines.
- **Line Strong** (#c2cbdd): control borders, table head rule, dividers inside bands.
- **Ink 2** (#465270): secondary text, labels, ledes below the hero.
- **Ink 3** (#66718c): placeholders, vak numbers, disclosure chevrons, the Nog geen oordeel dashed outline.
- **Hatch** (`repeating-linear-gradient(135deg, #f4f6fb 0 7px, #e6ebf5 7px 8px)`): Stale and Achterhaald rows and banners, the Overslaan tier.

### Named Rules
**The Committed Cobalt Rule.** Cobalt owns the top of every screen as one region: top bar plus full-bleed hero band, holding only the title, lede and the screen's first task. Below the hero, cobalt returns to links, focus, selection and the 3px top rule on figure bands. It never fills a primary button.

**The Ink Is Primary Rule.** The primary action is an ink button everywhere, including on the cobalt hero.

**The Vermilion Means Risk Rule.** Vermilion appears only for risk flags, errors, destructive actions, an unaffordable shortfall and the Harde afwijzing. Never for emphasis, never decoratively.

**The Ochre Means Caution Rule.** Ochre marks what deserves a second look but is not a risk: the Overwegen tier, minpunten, a seller's claim, thin grounding, an asking price above WOZ or comparables.

**The Directional Figure Rule.** Asking price against WOZ and comparables is ochre when above and green when below; Ruimte boven vraag is green when there is room and vermilion on a shortfall. Zero or unknown stays ink. The +/− sign is always printed, so colour is never the only cue.

**The Never Colour Alone Rule.** Every coloured state carries a shape, icon or sign and a Dutch word: tier glyphs (tick, ring, dashed ring, dash, ban), flag glyphs (round plus, square minus, triangle), a drawn alert mark before every error, a hatch for Stale, a +/− on every toned figure.

## Typography

**Display Font:** Archivo Variable (with Archivo, system-ui, sans-serif)
**Body Font:** Archivo Variable (same family)

**Character:** One grotesk across all roles, differentiated by its width axis: condensed and very heavy for titles and money, full width for reading and labels. Tabular figures are set on `:root` and inherited everywhere.

### Hierarchy
- **Display** (750, 56px, 1, wdth 78): the tier label on the Oordeel band only. 40px below 720px.
- **Headline** (750, 40px, 1.05, wdth 80): page titles in the hero (Woningen, Koperprofiel); the woning address grows to 48px. 28px below 720px.
- **Figure Large** (750, 48px, wdth 80): Openingsbod and Maximumbod. Key-figure band uses 32px at wdth 85; Gevolgen figures 26px at 650.
- **Figure** (650, 24px, 1.2): numbers in figure rows. Toned table cells step up to 600.
- **Title** (650, 20px, 1.3): section headings (h2). h3 is 15px at 650. The Dossier/Oordeel halves tabs use 17px at 650.
- **Body** (400, 15px, 1.5): everything else. Values in fact rows sit at 550. Ledes (16px) and prose cap at 68ch.
- **Prose** (400, 17px, 1.6): the Redenering text; tier summary 19px at 1.45, max 60ch.
- **Label** (550 to 600, 13px): table headers, figure labels, filter legends, rail titles. Sentence case, no tracking, never uppercase.

### Named Rules
**The Width Axis Rule.** Scale up by condensing as well as enlarging: anything 32px and above uses `font-stretch` between 78% and 85% at weight 650 to 750. Reading text stays at 100% width.

**The Tabular Everywhere Rule.** `font-variant-numeric: tabular-nums` is global; right-align numeric table cells, left-align numbers inside figure bands.

## Layout

A single 1320px raster, centred, with 32px side padding (16px below 720px); `main` has 96px bottom padding. The sticky top bar is 60px (56px narrow), solid hero cobalt with a white 22% hairline.

- **Hero band:** the first block of every screen is a `.hero` that bleeds to the viewport edges (a `::before` spanning `calc(50% - 50vw)` either side) and continues the top bar without a seam: 40px top, 36px bottom padding, 36px below it (24px all round below 720px). Screens without a hero start 40px below the bar.
- **Woningen:** hero with page head and the capture panel; then a wrapping filter toolbar (tier toggles, price fields, checkboxes, result count pushed right) and the comparison table with the tier pill in the first column. Below 1024px detail columns hide; below 720px each row becomes a three-column grid with `data-label` captions above numbers.
- **Woning header:** inside the hero: back link and stepper, the 48px address with city and meta, actions right, and the Dossier/Oordeel tabs sitting on the hero's bottom edge (no bottom padding).
- **Dossier:** a two-column grid, 272px sticky rail (Op deze pagina, source statuses, herkomst legend) beside the content, 56px gap. Below 1180px the rail folds above the content as an auto-fit row.
- **Fact rows:** fixed tracks `28px | 2fr | 3fr | 2.2fr` (vak number, label, value, stamp) so stamps align down the page; three tracks below 1024px, two below 720px.
- **Koperprofiel:** hero with the title and lede, then three columns `200px | 1fr | 300px` with 48px gaps: section index, form, sticky live Gevolgen. Below 1024px it collapses to one column with a section select; the save footer is sticky at the bottom.
- **Rhythm:** sections are separated by a 1px line with 28px above and 32px below the content. Inside groups, 8, 12, 16 and 24px steps; between page regions 32 to 40px.

**The Rule Not Box Rule.** Sections divide with a hairline on top, not a container. A tinted band is the only grouping device below the hero, and figure bands divide internally with vertical hairlines, not boxes.

## Elevation & Depth

Flat. Depth is tonal: the cobalt hero over white, a raised lighter cobalt panel inside the hero, tinted bands under ground, hatch for out-of-date content. Shadows exist only on things that float above the page.

### Shadow Vocabulary
- **Menu** (`box-shadow: 0 1px 2px rgb(18 20 23 / 0.08), 0 12px 32px -8px rgb(18 20 23 / 0.22)`): row action menus.
- **Dialog** (`box-shadow: 0 24px 64px -12px rgb(18 20 23 / 0.35)`): modal dialogs and the photo viewer, over a `rgb(18 20 23 / 0.36)` backdrop.
- **Inset rules** (`box-shadow: inset 0 0 0 1px` / `inset 0 -3px 0` / `inset 0 -4px 0` / `inset 0 3px 0`): hairline outlines, the nav and halves underlines, and the cobalt top rule on figure bands; not elevation.

### Named Rules
**The Only Floating Things Cast Shadows Rule.** Menus and dialogs have shadows; nothing resting on the page does.

## Shapes

Small, near-square corners. Controls, stamps and inputs use 6px; bands (capture panel, key figures, bid figures, Gevolgen, tier band, empty states) use 4px; dialogs 8px; tier pills, chips and signaal chips are full pills. The hero band itself is square and full-bleed. Borders are 1px, except where the style itself is the message: the 3px double rule (Register stamp, Harde afwijzing), 2px dotted (Verkoper stamp), dashed (Foto's stamp, file input, add button, Nog geen oordeel). The wordmark is a 22px rounded square split white over ink, sitting on cobalt.

## Components

### Buttons
Quiet and firm; one shape everywhere.
- **Shape:** gently squared (6px), 38px tall, 14px horizontal padding, weight 550.
- **Primary:** ink fill, white text; submit buttons are primary by default, on white and on the cobalt hero alike. Hover to Ink Hover.
- **Secondary:** white with a Line Strong border; hover fills Band and darkens the border to Ink 3; active fills Band Strong. In the woning header the border is hidden until hover.
- **Link:** cobalt text, underlined at 3px offset, no box.
- **Destructive:** vermilion text on a Vermilion Line border; hover fills Vermilion Tint.
- **Icon / row menu:** 34px square, borderless, Ink 2, Band on hover.
- **Small:** 30px tall, 13px text. **Add:** cobalt text, dashed border.
- **Focus:** 2px cobalt outline, 2px offset, globally; white inside the top bar and hero.

### Chips
- **Status chip:** 22px pill on Band, 12.5px Ink 2 text; Verkocht is ink-filled, Onder bod on Band Strong. In the hero, chips are white at 16% with white text.
- **Stale chip:** hatch ground with an inset Line Strong ring (solid white in the hero).
- **Signaal chip:** a 34px pill button with a flag glyph, linking a verdict to its supporting flag.

### Cards / Containers
There are no cards. Grouping uses bands: Band ground, 4px corners, 20 to 28px padding, no border, no shadow. The key-figures and Biedadvies bands carry a 3px cobalt top rule (inset shadow) and split with vertical Line Strong hairlines.

### Inputs / Fields
- **Style:** white, 1px Line Strong, 6px corners, 40px tall (46px in the capture field, 44px on narrow forms). Numeric inputs right-align.
- **Focus:** border turns cobalt plus a 3px Cobalt Halo ring. On the capture panel the input is borderless and focus shows a white border with a 3px white 45% ring.
- **Error:** vermilion border; the message below carries the drawn alert mark and vermilion 550 text. On the hero the error becomes a filled vermilion notice with white text.
- **Vak:** a labelled field (600, 14px label) with its small vak number as a reference mark in Ink 3.

### Navigation
- **Top bar:** cobalt; wordmark, then Woningen and Koperprofiel as full-height links in Hero Mist at 550; the current page is white with a 3px white underline. API state sits right in Hero Mist with a 7px dot.
- **Halves:** Dossier and Oordeel as 17px tabs with a muted sub-line, sitting on the hero's bottom edge; inactive in Hero Mist, active white with a 4px white underline.
- **Stepper and back link:** borderless text links in Hero Mist with lucide chevrons; the stepper fills Hero Raised on hover.

### Directional Figures
Asking price vs WOZ and vs comparables, and Ruimte boven vraag, take `.tone-favorable` (green), `.tone-concern` (ochre) or `.tone-shortfall` (vermilion) in the comparison table (at weight 600) and in the Dossier key figures. Values are always signed.

### Tier Mark (signature)
Five tiers, each a lucide shape plus its Dutch label: Zeker kopen (tick, green), Overwegen (ring, ochre), Nog geen oordeel (dashed ring, dashed outline), Overslaan (dash, hatch), Harde afwijzing (ban, vermilion). Inline it is a 28px pill; as a filter toggle it is a white pill that gains a 2px ink ring when checked; on the Oordeel it becomes the whole band (green, ochre fill, hatch, or vermilion tint with a double rule), with the 56px display label and a 48px glyph disc, revealed by a left-to-right clip wipe (420ms).

### Herkomst Stamp (signature)
A small 12.5px tag with a lucide icon and a word, its border telling trust: Register is a 3px cobalt double rule, Derde partij solid, Verkoper 2px dotted ochre with ochre text, Foto's dashed violet with violet text, Berekend a filled Band with no border, Advertentie solid. A legend in the dossier rail repeats all of them.

### Flag Glyph (signature)
20px: pro is a round green-tint plus, con (minpunt) a square ochre-tint minus with an ochre heading, risk a bare vermilion warning triangle. Flags list as hairline-divided disclosures with a rotating chevron.

### Motion
One easing, `cubic-bezier(0.22, 1, 0.36, 1)`. Hovers at 120 to 150ms, disclosures and tabs at 180ms, the tier band wipe at 420ms, cobalt-tint flashes at 900ms to 1.6s. Reduced motion collapses all to 1ms.

## Do's and Don'ts

### Do:
- **Do** open every screen with the cobalt hero band (#1a44c2) continuing the top bar, holding only the title, lede and the screen's first task.
- **Do** use white and #c9d7fc for text on cobalt, and a white focus outline there.
- **Do** group below the hero with a tinted band (#eef2fb, 4px corners) or a top hairline, never a bordered card.
- **Do** set titles and money in condensed heavy Archivo (wdth 78 to 85, weight 650 to 750).
- **Do** pair every coloured state with a lucide glyph, drawn mark or sign and a Dutch word from the GLOSSARY.
- **Do** colour directional figures green, ochre or vermilion and always print the +/− sign.
- **Do** mark herkomst by border style: double for register, solid for third party, dotted for seller, dashed for estimate, filled band for computed.
- **Do** show Stale and Achterhaald with the hatch, keeping the old content visible.
- **Do** make the primary action an ink button and every link cobalt.
- **Do** keep reading text under 68ch.

### Don't:
- **Don't** use vermilion for anything but risk, errors, destructive actions, a shortfall and the Harde afwijzing.
- **Don't** use ochre for anything but caution.
- **Don't** use cobalt fills for primary buttons.
- **Don't** wrap sections, figures or table rows in bordered, shadowed cards.
- **Don't** put a border on something unless the border's style is the information.
- **Don't** add shadows to resting surfaces; only menus and dialogs float.
- **Don't** set labels in uppercase, tracked small caps, or as kickers above headings.
- **Don't** use emoji or text characters as icons; glyphs are lucide or drawn CSS marks.
