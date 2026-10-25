---
name: Funda Griller
description: A Dutch house hunter's evidence file, set as a government form.
colors:
  ground: "#f6f7f9"
  surface: "#ffffff"
  ink: "#0e1f3a"
  ink-muted: "#4a5b73"
  rule: "#c3cad6"
  form-blue: "#154273"
  vermilion: "#c2410c"
  hatch-light: "#eef0f4"
  hatch-dark: "#dfe3ea"
  highlight: "#eef3fa"
  flash: "#dbe6f3"
typography:
  tier:
    fontFamily: "Source Sans 3 Variable, Source Sans 3, system-ui, sans-serif"
    fontSize: "28px"
    fontWeight: 600
  headline:
    fontFamily: "Source Sans 3 Variable, Source Sans 3, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 700
  figure:
    fontFamily: "Source Sans 3 Variable, Source Sans 3, system-ui, sans-serif"
    fontSize: "22px"
    fontFeature: "tnum"
  prose:
    fontFamily: "Source Sans 3 Variable, Source Sans 3, system-ui, sans-serif"
    fontSize: "16px"
    lineHeight: 1.5
  body:
    fontFamily: "Source Sans 3 Variable, Source Sans 3, system-ui, sans-serif"
    fontSize: "14px"
    fontFeature: "tnum"
  label:
    fontFamily: "Source Sans 3 Variable, Source Sans 3, system-ui, sans-serif"
    fontSize: "12px"
    letterSpacing: "0.04em"
  vak-number:
    fontFamily: "Source Sans 3 Variable, Source Sans 3, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 600
rounded:
  vak: "2px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
components:
  button-primary:
    backgroundColor: "{colors.form-blue}"
    textColor: "{colors.surface}"
    rounded: "{rounded.vak}"
    padding: "6px 12px"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.form-blue}"
    rounded: "{rounded.vak}"
    padding: "6px 12px"
  button-small:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.form-blue}"
    rounded: "{rounded.vak}"
    padding: "2px 8px"
  vak:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.vak}"
    padding: "6px 8px 8px"
  section-frame:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.vak}"
    padding: "16px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.vak}"
    padding: "6px 8px"
  stamp:
    textColor: "{colors.form-blue}"
    rounded: "{rounded.vak}"
    padding: "1px 4px"
  table-row:
    backgroundColor: "{colors.surface}"
    height: "32px"
    padding: "4px 8px"
---

# Design System: Funda Griller

## Overview

**Creative North Star: "Het Formulier"**

Every fact is a numbered *vak* on a Dutch government form, with its herkomst stamped in a fixed margin beside it. The Dossier reads like an aanslagbiljet: dense, ruled, auditable. The user reads it at a desk in daylight for twenty minutes before a high-stakes bid, so the system is light, ink-dark, and calm; nothing glows, nothing floats.

Brand lives in precise details rather than decoration: hairline rules, square corners, tabular figures, a three-letter stamp on every fact, and a tier mark that still reads in greyscale. If an element is not a vak, a rule, a stamp, or a number, it is not there. The look refuses the SaaS card grid and the dashboard widget.

**Key Characteristics:**
- Paper-grey ground, white vakken, navy ink, one Rijks-blue, one vermilion.
- 1px navy frames around sections and vakken; 2px corners at most.
- Every state (tier, Flag class, Stale, provenance) is encoded by shape, glyph and word first, colour second.
- Tabular numerals wherever money, area or a percentage appears.
- Dutch UI copy throughout, using the `_Dutch UI_` labels from `GLOSSARY.md`.

## Colors

A restrained palette: one accent for structure and action, one alarm colour held in reserve.

### Primary
- **Rijks Form Blue** (`form-blue`): primary buttons, link text, vak numbers, provenance stamps, focus ring, selected state. Never on inactive states.

### Secondary
- **Vermilion** (`vermilion`): Harde afwijzing, the Risico Flag, invalid vakken, error notices and destructive buttons. Nothing else.

### Neutral
- **Paper Grey** (`ground`): page background.
- **Form White** (`surface`): vak and section fill.
- **Navy Ink** (`ink`): text and the outer frame of sections, tables and vakken.
- **Muted Ink** (`ink-muted`): secondary text, notes, the computed (BER) stamp; 4.9:1 on ground.
- **Hairline Grey** (`rule`): row dividers, input borders, inner figure frames.
- **Hatch Greys** (`hatch-light`, `hatch-dark`): the 45° hatch wash for Stale facts, Achterhaald Oordelen and the Overslaan tier glyph; also the skeleton rows.
- **Blue Wash** (`highlight`, `flash`): a deep-linked fact or Signaal, and the one-shot refetch flash on a list row.

### Named Rules
**The Reserved Vermilion Rule.** Vermilion means "no" or "danger": Hard no, risk, invalid, destructive. A seller's claim, a third-party value or a sold house is never vermilion.

**The Colour Is Never Alone Rule.** Every coloured state also carries a glyph, a shape or a border style and a Dutch word. Convert the screen to greyscale; if a state disappears, it is a bug.

## Typography

**Body Font:** Source Sans 3 Variable, self-hosted via `@fontsource-variable/source-sans-3` (with `system-ui` fallback).

**Character:** one workhorse sans with tabular figures; hierarchy comes from size, weight and caps, never from a second face.

### Hierarchy
- **Tier** (600, 28px): the Oordeel tier label and the bid amounts in Biedadvies. Page title (h1) also sits at 28px.
- **Figure** (400, 22px, tabular): key figures and Betaalruimte values.
- **Headline** (700, 18px): screen titles (`Dossier: …`, `Oordeel: …`, Woningen).
- **Prose** (400, 16px, line-height 1.5, max 68ch): Oordeel summary and Redenering.
- **Body** (400, 14px, tabular): data rows, facts, table cells. Base size of the app.
- **Label** (600 in tables, 12px, uppercase, 0.04em tracking): vak labels, section headings (h3), table headers, figure labels.
- **Vak number** (600, 11px, form-blue): the number tag on each vak and fact row.

### Named Rules
**The Tabular Figures Rule.** Money, area, percentages and dates use `font-variant-numeric: tabular-nums` and right-align in tables, so columns can be compared by eye.

**The 68ch Rule.** Prose and explanatory paragraphs stop at 68ch; data rows run full width.

## Layout

Desktop-first, max width 1440px, 24px frame margin, 16px gutters, 8px inner spacing. Density is form-like: table and fact rows are 32px.

- **Dossier fact row:** a fixed four-track grid, `nr 48px | label 240px | waarde flex | herkomst-kantlijn 280px`. The kantlijn never moves. Below 720px it collapses to `32px | 1fr` with value and stamp stacked.
- **Woningen table:** fixed columns. Below 1024px the detail columns hide; below 720px each row becomes a three-column card grid and sorting moves to a select.
- **Koperprofiel:** three tracks, `section index 180px | vakken | Gevolgen 280px`, with index and Gevolgen sticky. Below 1024px it is one column, the index becomes a select, and controls grow to 44px.
- **Biedadvies:** three vakken side by side, stacking below 720px.
- Section order in the Dossier: header (tier mark, status, herkomst legend), key figures, Brondekking, Signalen, Betaalruimte, then the fact groups.

## Elevation & Depth

Flat. There are no shadows. Depth comes from framing and tone: white vakken framed in 1px navy on paper grey, hairline row rules inside, and the hatch wash for out-of-date content. Dialogs sit on a 30% navy scrim with the same 1px frame.

### Named Rules
**The Frame Not Shadow Rule.** To lift something, frame it. A 1px ink border separates; a hatch marks "older"; nothing casts a shadow.

## Shapes

Square form language: 2px radius on every vak, button, input, chip, stamp and dialog. Borders carry meaning. In stamps, double rule means official, single solid means stated, dotted means seller-stated and dashed means estimated. In tier glyphs, a fill means Zeker kopen, an outline Overwegen, a dashed outline Nog geen oordeel, a hatch Overslaan, and a double vermilion frame with a diagonal bar Harde afwijzing. The only round shape is the Pluspunt Flag glyph; the only triangle is the Risico glyph.

## Components

### Buttons
- **Shape:** square corners (2px), 1px form-blue border.
- **Primary:** solid form-blue with white text. One per screen section: Ophalen, Opslaan, Oordeel opvragen, and Oordeel opnieuw draaien when the Oordeel is Achterhaald.
- **Secondary:** white with a form-blue border and text: navigation (Terug naar …) and secondary actions.
- **Small:** 12px, 2px 8px padding, for per-row actions such as per-Bron refetch.
- **Destructive:** vermilion border and text, only inside a confirm Dialog.
- **Link button:** underlined, semibold form-blue, used for the address that opens a Dossier.
- **Focus:** a 2px form-blue outline at 2px offset on every focusable element. Disabled: 60% opacity.

### Vak (signature component)
A white box with a 1px navy frame and an 11px form-blue number tag before a 12px caps label, then the control, then a hint or an error line. When invalid, the frame turns vermilion and the error line starts with `!`. Fact rows in the Dossier are the read-only vak: a 32px row on the four-track grid.

### Herkomst stamp (signature component)
A 12px inline box in the kantlijn: glyph + three-letter code (aria-hidden) + Dutch word + date, with a full sentence as its accessible name. Variants:
- **ADV** ■ single border (listing)
- **BRN** ◆ double border (register, official)
- **3DE** ◇ single border, value prefixed `~`, "onofficieel"
- **VRK** ❝ dotted border, links to the Document page
- **OBS** ◔ dashed border, value prefixed `≈`, "geschat"
- **BER** = muted border (computed)
- **VGL** ⇄ (comparable woning)

A stale fact strikes its date and adds ⏲ Verouderd. A one-line legend of every code sits under the Dossier header.

### Tier mark
Glyph box + Dutch label. In the list and the Dossier header it is compact (18px glyph, 14px label). On the Oordeel it is large (36px glyph, 28px label).

### Signaal (Flag)
Grouped in Pluspunt, Minpunt and Risico bands, each with a shape glyph (circle +, square −, vermilion triangle !). Each row is a disclosure showing the rule id and version plus evidence lines with "Zie vak N" links. In the Redenering, Signaal chips are outlined buttons that jump back to the Signaal.

### Tables
A 1px navy outer frame and hairline row dividers, with 12px caps headers that sort through header buttons (`aria-sort`). Rows are keyboard-focusable. A stale row carries the hatch plus a 4px ink bar on its first cell; a sold row strikes the address and adds a status chip.

### Inputs
1px hairline border, 2px corners, 6px 8px padding, tabular numerals. Invalid inputs get a vermilion border plus `aria-invalid` and a described-by error line.

### Banners and notices
- **Error notice:** vermilion, semibold, prefixed `!`, `role="alert"`.
- **Status banner:** 1px ink frame on white, with a semibold status chip. Used for Achterhaald (plus a 4px inset ink bar) and for a sold or under-offer woning on the Oordeel.
- **Harde afwijzing:** 4px double vermilion frame with ✕.

## Do's and Don'ts

### Do:
- **Do** encode every state with glyph + shape or border + Dutch word; colour is the third cue.
- **Do** keep the herkomst kantlijn at 280px and in the same column on every fact row.
- **Do** use the hatch tokens (`hatch-light`, `hatch-dark`) for anything older or skipped, never a new grey.
- **Do** use the `_Dutch UI_` label from `GLOSSARY.md`: Verouderd only for a Stale fact, Achterhaald only for a Verdict or Case built on older inputs.
- **Do** move focus to the screen heading and set `document.title` when switching between Woningen, Dossier and Oordeel.

### Don't:
- **Don't** use vermilion for anything but Hard no, risk, invalid input or destructive actions.
- **Don't** add shadows, gradients, rounded cards or a second typeface.
- **Don't** put more than one solid primary button in a screen section.
- **Don't** use a coloured side stripe as decoration. The 4px ink bar is reserved for Stale and Achterhaald.
- **Don't** hide or dim Stale facts below 4.5:1 contrast.
