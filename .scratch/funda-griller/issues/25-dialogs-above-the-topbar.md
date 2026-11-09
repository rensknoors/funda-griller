# 25: Dialogs above the topbar

**What to build:** The photo viewer opens underneath the sticky topbar. The topbar stays fully lit above the backdrop and covers the top of the viewer, so **Foto N** sits cut off under it. Every dialog should cover the whole app, the topbar included.

**Status:** resolved

### Cause

`.topbar` is `position: sticky; z-index: 20` (`frontend/src/styles.css:76`). `.dialog-backdrop` and `.dialog` (`styles.css:259-261`) are `position: fixed` with no `z-index`, so the topbar stacks over them even though Base UI portals them to the end of `body`. `.photo-dialog` sits at `top: 4%` (`styles.css:438`), so the topbar's ~76px hides its title. `.capture-tray` (`z-index: 20`, `styles.css:648`) has the same problem.

### Acceptance criteria

- [x] The dialog backdrop dims the topbar and the capture tray as well as the page
- [x] Every dialog popup, the photo viewer included, stacks above the topbar and capture tray; its title and **Sluiten** are fully visible at 1280×800 and at phone width
- [x] One stacking order in `styles.css` (for example `--z-topbar`, `--z-tray`, `--z-dialog` tokens) instead of loose numbers, so a new overlay can't land under the topbar again
- [x] Menus that open inside a dialog still show above it

### Tests

- [x] e2e: open the photo viewer from the woning header; the dialog title is visible and not covered by the topbar (for example `elementFromPoint` at the title's centre returns the title)

## Comments

Reported from a screenshot of the Dossier for Céline, Sittard: the viewer's **Foto 1** title cut off under the blue topbar, Woningen / Koperprofiel still bright above the backdrop.
