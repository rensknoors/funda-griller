# 24: Photo cards and figure graphics

**What to build:** Make the app more graphic. Show Woningen as photo cards the way funda does, lead the woning header with its photos, and draw the figures that are read against each other.

**Blocked by:** 23 (A calmer Woningen list and Ophalen in the background)

**Status:** resolved

### Woningen as cards

- [x] Cards by default, with a **Kaarten / Lijst** switch remembered per browser; Lijst is the table from ticket 23
- [x] A card shows the first photo (a house glyph on hatch when there is none) with the tier, actions and photo count on it, then Vraagprijs with signed Ruimte, address, city and status, m² wonen and perceel, energy label, Signalen and t.o.v. WOZ
- [x] A Harde afwijzing shows its deal-breaker; Verkocht greys the photo, Verouderd puts a chip on it, an archived card fades
- [x] The whole card opens the Dossier; energy labels use the register's A to G colours, in the cards and in the list

### Photos in the woning header

- [x] Dossier and Oordeel show the first photo large in the hero with four thumbnails, the last one +N
- [x] A photo viewer steps through every photo with arrow buttons and ←/→, with **n van N**; Foto-waarnemingen uses the same viewer

### Figure graphics

- [x] Dossier: a price scale under the key figures with the Vraagprijs, WOZ-waarde, Vergelijkbaar and Jouw maximum, the room or shortfall shaded
- [x] Betaalruimte: a bar of what comes on top of the Vraagprijs (overdrachtsbelasting, vaste kosten, Direct nodig onderhoud)
- [x] Verbouwingskosten: range bars per urgency on one shared scale
- [x] Oordeel: a scale from Openingsbod to Maximumbod with the Vraagprijs and comparables' value
- [x] Koperprofiel Gevolgen: each Woning's Vraagprijs against the budget being typed, and how many fit
- [x] Every graphic repeats its figures for screen readers

### Empty state and design system

- [x] An empty Woningen list shows the three steps to a first Dossier
- [x] `DESIGN.md` describes the Woning card as the only card, the photo header and the figure graphics

### Tests

- [x] e2e: cards by default with tier, price, deal-breaker, WOZ figure and photo; the view choice is remembered; the header photo opens the viewer and steps to the next photo
