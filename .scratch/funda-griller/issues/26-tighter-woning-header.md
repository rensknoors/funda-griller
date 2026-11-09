# 26: A tighter woning header

**What to build:** The woning header on Dossier and Oordeel wastes most of the hero. The address block is bottom-aligned (`align-items: end`) in a wide left column beside a 440px photo column, so a ~300px empty field of cobalt sits above the address, and a wide gap separates the text from the photos. Make the photos and the facts fill the hero, so it is shorter and every part of it carries something.

**Blocked by:** 25 (Dialogs above the topbar), since both change the hero

**Status:** resolved

### Design: a gallery band

```
← Terug naar woningen                                  ‹ Vorige woning   Volgende woning ›

Céline                          ┌──────────────────────┬──────────┬──────────┐
Klinkenberghstraat 16           │                      │          │          │
Sittard  (–) Overslaan          │                      ├──────────┼──────────┤
Advertentie van 29 okt · v5     │      first photo     │          │   +45    │
                                │                      │          │          │
128 m² wonen · 312 m² perceel ·[C]                     │          │   📷 50  │
                                │                      │          │          │
[⟳ Opnieuw ophalen] [⤓ Exporteer ▾]└──────────────────┴──────────┴──────────┘

Dossier            Oordeel
feiten en bronnen  uitkomst en biedadvies
```

- **Two columns that share one height.** `.woning-title.with-photos` becomes `minmax(0, 5fr) minmax(0, 7fr)` with `align-items: stretch`. The photos set the height; the text column is a flex column that fills it: address and meta at the top, actions on the photos' bottom edge.
- **The funda mosaic.** The first photo fills the left half of the photo block, at full block height. Four thumbnails sit 2×2 to its right, the last one showing +N, the photo count on the last one. The block is `clamp(260px, 26vw, 360px)` tall and the photos use `object-fit: cover`. This replaces the photo-above-a-strip-of-thumbnails layout, which made the hero about 470px of photo.
- **The address breaks over two lines on purpose.** 48px with `text-wrap: balance`, so a long street name fills the column's height instead of a single line with emptiness above it.
- **A fact line under the meta:** m² wonen · m² perceel · the energy label chip in the register's A to G colours, all from the latest snapshot. Leave out any fact that's missing. Don't add the Vraagprijs: it opens the key figures band directly below.
- **One action row.** "Koperprofiel meesturen" now dangles under the export button and breaks the row. Make **Exporteer als Markdown** a menu button (the existing `.menu`) with a checked **Koperprofiel meesturen** item and a **Downloaden** item. Same download URL as now.
- **Less dead padding.** `.woning-nav` margin 20 → 16px, `.halves` margin-top 28 → 24px.
- **Without photos:** one column, address and fact line at full width, no reserved photo space.
- **Below 720px:** the photos stack above the address, as now: the first photo at 3:2 full width, the thumbnails as one row of four beneath it.

### Acceptance criteria

- [x] At 1280×800 with photos, the hero from the woning nav to the bottom of the tabs is at most ~480px tall, and no cobalt area larger than the gutters is empty beside or above the address
- [x] The text column's top lines up with the photo block's top, and the action row's bottom lines up with the photo block's bottom
- [x] The photo mosaic: the first photo large, four thumbnails 2×2, +N on the last, each opening the photo viewer at that photo
- [x] The fact line shows wonen, perceel and energy label when present, and leaves out each one that's missing
- [x] Export is one menu button with the Koperprofiel meesturen toggle inside; the download still carries `with_profile` as before
- [x] Without photos and below 720px it lays out as described above
- [x] `DESIGN.md`'s Woning header paragraph describes the gallery band

### Tests

- [x] e2e: the header photo opens the viewer and a thumbnail opens it at its own photo (update the ticket 24 test for the mosaic)
- [x] e2e: export with Koperprofiel meesturen turned off downloads without the profile (update `export.spec.ts` for the menu)
- [x] e2e: the fact line shows the snapshot's living area, plot area and energy label

## Comments

Reported from a screenshot of the Dossier for Céline Klinkenberghstraat 16, Sittard: the address sits low at the left with an empty cobalt block above it, and the photos sit far to the right.

Implemented as a gallery band. At 1280×800 the hero from the woning nav to the bottom of the tabs measures 477px. The e2e fixture has only two photos, so the 3- and 4-thumbnail mosaics and the no-photo layout are covered by CSS but not seen in a screenshot. The export menu keeps the uncommitted "Koperprofiel meesturen" label (without "(geanonimiseerd)"). The energy label in the fact line is the advertentie's, as the ticket asked; the register's may differ (the Dossier shows both).
