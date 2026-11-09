# 23: A calmer Woningen list and Ophalen in the background

**What to build:** The Woningen list shows too many figures at once, Ophalen gives no sign of what it is doing, and the filter chips look different from the tier chips in the rows. Show the key figures per row and fold out the rest, run a capture in the background with visible progress on every page, and give the filter chips and row chips one style.

**Blocked by:** 15 (Listings comparison view)

**Status:** resolved

### Rows that fold out

- [x] A row shows the Oordeel, address (city, status, Verouderd count), Vraagprijs and Signalen
- [x] t.o.v. WOZ, t.o.v. vergelijkbaar, Ruimte boven vraag, Direct nodig, m² woon / perceel, Label and Opgehaald fold out below the row: by clicking the row, the chevron, or →/← on a focused row
- [x] **Alles uitklappen** in the header; ↑/↓ skip the fold-out rows
- [x] The header sorts by Oordeel and Vraagprijs; a **Sorteren** select, always visible, sorts by every other figure

### Ophalen in the background

- [x] `GET /api/listings/captures` lists running captures and refetches with their current step (`listing`, `photos`, `sources`, `observations`, `brochure`), held in memory and cleared when the capture ends, failed or not
- [x] The capture field clears at once; several captures can run side by side
- [x] A tray in the corner of every page shows each capture: name, **Stap n van 5** with the step's Dutch label, a five-part bar and the elapsed time; it keeps running while the user moves to a Dossier or the Koperprofiel
- [x] Done: **Opgehaald** with **Dossier openen**, leaving after 10 seconds. Failed: the error stays until closed, with **Handmatig invoeren** when the provider is blocked
- [x] A refetch from a row shows in the tray too

### One tier chip

- [x] Filter chips use the tier colours of the row chips; a checked chip gets a ring in its own colour and the others fade
- [x] Rows show the tier as a glyph-only chip, its label in a tooltip and for screen readers

### Tests

- [x] API tests: a running capture reports its step and disappears when done; a failed capture stops being reported
- [x] e2e: a capture keeps reporting progress while navigating to the Koperprofiel, then opens its Dossier; list specs fold a row out before reading its figures
