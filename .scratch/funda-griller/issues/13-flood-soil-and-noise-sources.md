# 13: Flood, soil and noise Sources

**What to build:** Two more Sources feed the Case: flood and soil risk for the address, and noise levels. They follow the same fetch-date, Stale and manual-refetch behaviour as the first Sources, and trigger Flags where they cross thresholds.

**Blocked by:** 07 (Energielabel and WOZ Sources)

**Status:** resolved

- [x] Flood and soil risk facts appear in the Case for a Listing's coordinates
- [x] Noise levels appear in the Case
- [x] Both carry fetch dates, respect time-to-live and refetch manually
- [x] At least one Flag rule per Source raises a risk or con above a threshold
- [x] A failing or unavailable Source degrades gracefully as in ticket 07
- [x] Fixture-based API tests cover each Source and its Flag

## Notes

- Both Sources query a public WMS with GetFeatureInfo (WMS 1.3.0, `CRS:84`, a ~100 m box around the Listing's coordinates, centre pixel, `INFO_FORMAT=application/json`); no API key. Without coordinates a Source is skipped (`no_coordinates`). Request and response shapes were checked against each service's GetCapabilities, GetLegendGraphic and a live GetFeatureInfo on 2026-10-24; tests use fixtures only.
- `flood_soil` (Klimaateffectatlas, `cas.cloud.sogelink.com/.../kea_public/wms`): `flood_depth_m` from `maximale_waterdiepte_nederland_kleine_kans_20260128` (LIWO maximum water depth, small-chance scenario, metres; the raster's no-data `-9999` reads as 0), `subsidence_mm_per_year` from `nl_bodemdaling_totaal_v20260623` (`snelheid`, sign flipped so sinking is positive), `pile_rot_risk_pct` from `risicopaalrot_huidig` (`no_cc_risi`, share of the buurt's buildings at risk of pile rot, current climate).
- `noise` (RIVM Atlas Leefomgeving, `data.rivm.nl/geo/alo/wms`): Lden 2020 in dB for all sources, road, rail and air (`rivm_20220601_Geluid_lden_*_2020`, `GRAY_INDEX`); 0 is the map's no-data value and yields no fact.
- Both are official public maps (`trust: official`). TTL 365 days each (existing `source_ttl_days`); Stale, per-Source refetch and failure handling are the ticket 07 machinery.
- Flag rules (new condition kind `above`; rule set version 2), thresholds from each map's own legend: `flood_depth_high` risk above 0.5 m, `pile_rot_risk_high` risk above 6% ("hoog"), `subsidence_significant` risk above 5 mm a year ("significant"), `noise_high` con above 60 dB ("tamelijk slecht" from 61). Each names deal-breaker aliases (overstroming, fundering/paalrot, bodemdaling, geluid/lawaai).
- Dossier: new fact group **Omgeving** with both Sources; a skipped or failed Source says so in place.
- Deferred: Klimaateffectatlas layer names are dated and will be superseded (constants in `source_clients.py`); soil contamination (Bodemloket) not included, its WMS endpoint could not be verified from official docs; differential settlement (`risicoverschilzetting_*`) only exists for 2050 scenarios and is left out; neither adapter has run end to end inside the app against the live services.
