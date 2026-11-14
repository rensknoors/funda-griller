# 05: Verwachte verkoopprijs in Dossier, Biedadvies and Woningen

**What to build:** Spec "UI (Dutch)". Dossier block Verwachte verkoopprijs (value, range, basis, Zwak onderbouwd, Prijsstelling). List and cards: "Ruimte boven verwachte prijs" with its sort key, "–" plus "Haal vergelijkbare woningen op" when absent. Biedadvies: maandlasten bij verwachte verkoopprijs; without one, Voorwaarden only plus "Haal vergelijkbare woningen op voor een Maximumbod". Markdown export follows.

**Blocked by:** 02, 04

**Status:** ready-for-agent

- [ ] Dossier block per spec
- [ ] List, cards and sort key renamed and fed by the new headroom
- [ ] Biedadvies monthly costs at the Expected Sale Price; conditions-only state without one
- [ ] Markdown export carries Verwachte verkoopprijs and Prijsstelling
- [ ] e2e: Dossier shows the block; list sorts by the new headroom; conditions-only Biedadvies
