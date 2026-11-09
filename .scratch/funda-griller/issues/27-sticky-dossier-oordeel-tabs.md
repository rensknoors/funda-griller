# 27: Sticky Dossier and Oordeel tabs

**What to build:** The Dossier/Oordeel tabs (`.halves`) scroll away with the hero. On a long Dossier you have to scroll all the way back up to switch to the Oordeel. Keep the tabs pinned directly under the sticky topbar once the hero scrolls past, so the switch is always one click away.

**Blocked by:** 26 (A tighter woning header), since both change the hero and `.halves`

**Status:** resolved

### Current state

- `.topbar` is `position: sticky; top: 0; z-index: 20`, 60px tall (56px below 720px) (`frontend/src/styles.css:76-78`, `:595`).
- `.halves` is a plain flex `nav` at the bottom of the woning header (`WoningHeader.tsx:82`, `styles.css:326-330`), so it leaves with the hero.
- `.dossier-rail`, `.section-index` and `.gevolgen` stick at `top: 84px` (`styles.css:334`, `:494`), which assumes only the topbar is pinned.

### Design

- **A cobalt tab bar under the topbar.** `.halves` becomes `position: sticky` at the topbar's height, full-bleed cobalt (Hero) like the hero band, so it reads as part of the top region rather than floating over the white sheet. The tabs keep their place on the hero's bottom edge while the hero is in view.
- **Compact when pinned.** Once stuck, drop the muted sub-line (`.halves-note`) and tighten the padding, so the pinned bar is ~44px, not the full ~70px. Detect stuck with an `IntersectionObserver` sentinel, not a scroll listener.
- **Address in the bar when pinned (optional):** the street and house number in small Hero Mist type at the right, so you still know which Woning you're on. Leave out if it crowds phone width.
- **One sticky offset.** Add `--topbar-h` and `--tabs-h` tokens; the topbar, `.halves` and the rails (`top: calc(var(--topbar-h) + var(--tabs-h) + 24px)`) all read them, replacing the hard-coded `84px`. Anchor jumps from **Op deze pagina** use `scroll-margin-top` from the same tokens so a section heading doesn't land under the bar.
- **Stacking:** the tab bar sits under the topbar and under every dialog (use ticket 25's z-index tokens).

### Acceptance criteria

- [x] Scrolling a Dossier or Oordeel down keeps Dossier/Oordeel visible directly under the topbar, at 1280×800 and at phone width
- [x] The pinned bar is full-bleed cobalt, compact (no sub-line), and the active tab keeps its white underline
- [x] At the top of the page the header looks as it does now (or as ticket 26 leaves it)
- [x] The Dossier rail, section index and Gevolgen stick below the tab bar, not under it
- [x] Clicking an **Op deze pagina** link lands the section heading fully visible below the tab bar
- [x] Dialogs still cover the tab bar
- [x] Sticky offsets come from `--topbar-h` / `--tabs-h` tokens; no `84px` left in `styles.css`
- [x] `DESIGN.md`'s Halves and Woning header entries describe the pinned bar

### Tests

- [x] e2e: on a Dossier, scroll to the bottom; the Oordeel tab is visible and not covered (`elementFromPoint` at its centre returns the link), and clicking it opens the Oordeel
- [x] e2e: click an **Op deze pagina** link; the target heading's top is below the tab bar's bottom

## Comments

Reported from a screenshot of the Dossier for Céline Klinkenberghstraat 16, Sittard: the Dossier/Oordeel tabs sit at the bottom of the hero and scroll out of view.

Done. The tabs moved out of the `header` into a sibling `nav`, since a sticky element can't outlive its parent. They pin within the Dossier/Oordeel `section`. The only `84px` left in `styles.css` is the width of Foto-waarnemingen thumbnails, not an offset. The Koperprofiel's section index and Gevolgen have no tabs above them, so they stick at `--topbar-h + 24px`.
