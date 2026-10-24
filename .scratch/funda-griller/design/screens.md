# Shaped briefs: four screens

World, tokens, provenance, Stale, Flag and tier encodings are in `direction.md`. All screens are **Operate**, desktop-first, Dutch copy. Briefs state intent, not CSS.

Shared state vocabulary (every screen): **leeg** (empty, teaches the next action), **laden** (skeleton rows in the real layout, no centred spinner), **fout** (inline, says what failed and what to do), **verouderd** (Stale, shown on the fact and rolled up to the container).

---

## 1. Koperprofiel (Buyer Profile form)

**Job:** enter finances and preferences once; edit any time to see Cases re-evaluate. Rare, high-stakes, private.
**Success:** a correct profile with no silent typos; understanding what changed after an edit.

**Information architecture.** One page, numbered vakken in five sections: Huishouden, Inkomen, Vermogen en eigen woning (waarde, hypotheek, verkoopkosten, overwaarde berekend), Wensen (must-haves, nice-to-haves, deal-breakers), Reizen (pendelbestemmingen) plus Verbouwtolerantie (instap-klaar vs project, a 5-step Radio group). Left sticky section index; right a sticky **Gevolgen** panel with live derived figures (max hypotheek, overwaarde, budget) and the rules year. Footer bar: Opslaan, and a note "Opgeslagen op dit apparaat, nooit geüpload".

**Main interactions.** Inline validation on blur (bedrag buiten bereik, hypotheek hoger dan woningwaarde, lege verplichte vakken); error text under the vak with `!` glyph. Deal-breakers and wensen are repeatable rows (add, reorder with keyboard, remove). Saving shows a diff summary: "Dit verandert 3 oordelen" with link to the list; re-evaluation is explicit, nothing recomputes silently.

**States.** Leeg (first run): section 1 open, others collapsed with one-line hints, Gevolgen panel shows "Vul inkomen in om je budget te zien". Laden: vakken skeleton. Fout (load/save failure): inline banner with Opnieuw proberen, input preserved. Ongeldig: save disabled with count of problems and jump link to the first. Stale does not apply (no fetched facts); the rules year is shown and flagged `verouderd` if the table year is not the current year.

**Narrow.** Index becomes a top select; Gevolgen collapses to a bottom drawer-free accordion above the footer; vakken stack single column.

---

## 2. Woningen (Listings list and comparison view)

**Job:** see all candidates, rank them, decide where to spend attention, refetch stale ones, drop the dead.
**Success:** within 5 seconds know the best two candidates and which ones have old data.

**Information architecture.** Top bar: URL paste vak with Ophalen (primary). Below: filter row (tier multi-select, prijs min/max, `alleen verouderd`, `toon gearchiveerd`) and result count. Then the table. Columns fixed order: Oordeel (tier mark) | Adres (+ plaats, status chip) | Vraagprijs (+ prijsverloop arrow) | t.o.v. WOZ (%) | t.o.v. vergelijkbaar (%) | m² woon / perceel | Label | Ruimte boven vraag (headroom) | Signalen (+ − ! counts) | Data (verouderd count, laatst opgehaald). Default sort: tier order, then price ascending. Header click sorts; sort state has an arrow glyph and `aria-sort`.

**Reads at a glance.** Tier mark first so rows form bands. Numbers right-aligned tabular. Percent deltas signed with ▲/▼ glyph and word in the header tooltip, never colour only. The best tier rows get no extra ornament; Hard no rows show the triggering deal-breaker as the second line under the address.

**Main interactions.** Paste URL and Enter: row appears at top as laden skeleton; duplicate URL opens an inline notice on the existing row ("Al in je lijst. Opnieuw ophalen?"). Row click opens Dossier. Row menu: Opnieuw ophalen, Archiveren (confirm Dialog), Oordeel opnieuw draaien. Arrow keys move row focus, Enter opens. After refetch, a changed field flashes a 200 ms highlight and a status change (beschikbaar to verkocht) restyles the row: struck address, chip "Verkocht", ink lowered but ≥4.5:1.

**States.** Leeg: one vak with the paste field and three-line explanation of what happens next; no illustration. Laden: skeleton rows. Fout per row: "Ophalen mislukt: ongeldige URL / woning verwijderd / aanbieder geblokkeerd" (three distinct messages, ticket 04), row stays with last good data. Verouderd: hatched left edge on the row and `3 verouderd` in the Data column; header filter surfaces them. Gearchiveerd hidden by default with a count link.

**Narrow.** Below 1024 the columns Label, m², Signalen collapse into an expandable detail line. Below 720 the table becomes cards: tier mark left, address and price top, deltas second line, Data line bottom; sorting moves to a select.

---

## 3. Dossier (Case detail)

**Job:** audit the evidence for one house, judge how far to trust each fact, find the problems fast.
**Success:** the user can say what is wrong with this house, where the claim came from, and what is missing, without reading every fact.

**Information architecture (top to bottom).**
1. **Header strip.** Address, status chip, photo thumbnail strip link, tier mark (links to Oordeel), key figures: vraagprijs, t.o.v. WOZ, t.o.v. vergelijkbaar, ruimte boven vraag, maandlasten bij vraagprijs. Actions: Opnieuw ophalen, Oordeel bekijken.
2. **Brondekking bar.** One line: `7 bronnen: 5 gelukt, 1 mislukt, 1 overgeslagen`, each a small stamp with glyph + word (✓ gelukt, ✕ mislukt, – overgeslagen) and Opnieuw proberen on failures. Legend for herkomst codes pinned right.
3. **Signalen.** Three labelled bands in fixed order Pluspunt, Minpunt, Risico (the ticket's order); each band lists Flag titles one per line with count in the band header. Row expands to rule id, version and evidence links ("Zie vak 14", which scrolls and highlights that vak).
4. **Feiten.** Named groups (Kenmerken, Prijs en waarde, Energie en milieu, Omgeving, Verkoper-informatie, Foto-waarnemingen), each a collapsible section with a summary line and rollups: `12 feiten · 2 verouderd · 3 geschat`. Every fact is a row on the four-track grid (nr | label | waarde | herkomst-kantlijn). Groups default: open where a Flag or Stale lives, closed otherwise.
5. **Documenten panel.** List of uploaded Documents with status (gelezen, kon niet gelezen worden), upload, verwijder; Findings link back to their vak.
6. **Prijsverloop** small step chart with a data table fallback.

**Sticky aids.** Left group index with per-group rollup badges; filter bar (herkomst class chips with counts, `alleen verouderd`, `alleen geschat`). Filters are toggle buttons with pressed state shown by glyph (☑) and aria-pressed.

**Main interactions.** Expand Flag, jump to evidence, click a stamp to open Popover (bron, URL, opgehaald op, TTL, "onofficieel" note for WOZ, photo thumbnail or page link for OBS/VRK). Photo Observation opens the cited photo in a Dialog viewer. Refetch per Source or whole Dossier; fresh values highlight for 200 ms. Nothing refreshes by itself.

**Provenance in practice.** Fact row example: `14 | WOZ-waarde 2024 | ~ € 412.000 | ◇ 3DE WOZ-loket · onofficieel · 12 mrt`. A model estimate: `31 | Keuken | ≈ 20+ jaar oud | ◔ OBS foto 3, 7 · geschat`. A seller claim: `42 | Asbest | “Aanwezig in dakplaten” | ❝ VRK Vragenlijst p. 7 · door verkoper`.

**States.** Leeg (no Documents/Observations yet): section stays with a one-line prompt "Nog geen documenten. Upload de Vragenlijst." Laden: header and groups as skeleton, filled progressively per Source. Fout: Source row failures in the Brondekking bar, missing groups show "Bron mislukt, geen gegevens" in place, never silently absent. Verouderd: the stamp treatment from `direction.md`, with group and header rollup, so a stale Dossier is visible from the header.

**Narrow.** Index → top select; filter bar → collapsible; fact row stacks with the kantlijn as a stamp line under the value; Flags stay as expandable lines.

---

## 4. Oordeel (Verdict page)

**Job:** get the answer and the numbers to bid with, and understand why.
**Success:** the user leaves with a tier, an opening bid, a Maximumbod, and conditions, and can trace each claim to a Signaal.

**Information architecture.**
1. **Tier block.** Large tier mark (28px label + mark) and one-sentence summary. A Hard no shows the triggering deal-breaker as the headline reason, states "Deterministisch toegepast, geen model gebruikt", and omits Biedadvies.
2. **Redenering.** Prose, ≤68ch, with inline Signaal chips (glyph + title) that scroll to the Signaal in the Dossier. Provenance-aware: sentences leaning on a seller claim carry the `❝ VRK` mark.
3. **Biedadvies.** Three vakken side by side: Openingsbod, Maximumbod (derived from vergelijkbaar + betaalruimte, with a "hoe berekend" expander showing both inputs), Voorwaarden (checklist: financieringsvoorbehoud, bouwkundige keuring, Document-opvolging items). Beneath: maandlasten bij vraagprijs and bij Maximumbod, ruimte boven vraag, rules year/version.
4. **Versie-stempel.** Which Dossier snapshot, Koperprofiel version, rules version and model produced this; older Oordelen list with diff of tier and numbers ("Was Overwegen, nu Zeker kopen: inkomen +€ 5.000").
5. Actions: Oordeel opnieuw draaien (primary only when inputs changed), terug naar Dossier.

**States.** Leeg (no Verdict yet): explains it needs a Dossier and profile, button Oordeel opvragen. Laden: tier block skeleton with "model leest dossier" status line; Biedadvies appears after. Fout: model error or invalid response shown inline with Opnieuw proberen, last valid Oordeel kept and labelled `achterhaald` with its inputs. Achterhaald: if the Dossier or profile changed since, a banner "Dit oordeel is gebaseerd op een oudere versie" with a re-run action and the hatched wash on the tier block.

**Narrow.** Biedadvies vakken stack; Redenering stays prose; version history becomes an accordion.

---

## Cross-screen consistency

- One vak component, one stamp component, one tier mark, one Signaal glyph set, one table row pattern.
- Same four-track idea on form and Dossier; fixed columns on list.
- Primary action is solid blue once per screen section; never two competing.
- Destructive actions (archive, remove Document) always behind a Dialog with named consequence.

## Throwaway prototype

Not run. The two screens most at risk (Dossier fact density, list comparison) are settled by a fixed-track grid reused from the list and form, with rollups and defaults that reduce visible rows. Reopen with the `prototype` skill if ticket 15 or 06 finds the 280px kantlijn too wide at 1280 wide viewports; the fallback variant is a kantlijn that collapses to the stamp glyph with detail in the Popover.
