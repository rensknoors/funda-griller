# 31: Own offered mortgage rate in the Buyer Profile

**What to build:** The mortgage rate is one market snapshot (`[market_rate]` in `config/affordability.toml`, Van Bruggen index 2026-11-02, with NHG 4,40%, without 4,78%), edited by hand. The rate that actually counts for a household is the one in their own offerte. Let the household enter the rate they were offered, with and without NHG, as an optional override in the Buyer Profile. When a field is blank, the market snapshot applies as now. Every figure says which rate it rests on.

**Blocked by:** none

**Status:** ready-for-agent

### Current state

- `MarketRate` (`backend/app/affordability.py:57`) is loaded from `[market_rate]` by `load_rules` (`backend/app/rules_loader.py:34`) and shared by all year tables.
- `_capacity` (`backend/app/affordability.py:206`) runs `_norm` twice, at `market_rate.nhg` and at `market_rate.no_nhg`; the NHG route is capped at the NHG limit and the larger route wins. The monthly cost (`mortgage_rate`) uses the rate of the route taken.
- `_test_rate` (`backend/app/affordability.py:169`): under ten years fixed, `max(toetsrente, offered)`; ten years or longer, the offered rate.
- The Case shows "hypotheekrente van <as_of>" (`frontend/src/CaseView.tsx:506`) and "tegen x%" (`:542`).
- Changing the snapshot needs a `version` bump in the TOML before existing Oordelen show Achterhaald.

### Design

- **Buyer Profile (finances, also `FinanceDraft`):** two optional fields, `offered_rate_nhg` and `offered_rate_no_nhg` (fraction, e.g. `0.0425`; validated within a sane range, say 0,5% to 15%). Either, both or neither may be set; each field overrides only its own route.
- **Affordability:** `_capacity` and the monthly cost take the household's rate per route when set, else `rules.market_rate`. `_test_rate` is unchanged: under ten years fixed the lender still tests at least at the AFM toetsrente, also with an own rate. The rules summary and `Affordability` record per route where the rate came from (`own` / `market` with `as_of`).
- **Staleness:** the fields are part of the Buyer Profile, so saving a changed rate bumps the profile version and existing Oordelen show **Achterhaald** (`verdict.py:173`), as any profile change does.
- **LLM:** the rates may reach the LLM. `reduce_profile` gains the rate per route actually used and its source (own or market), so the Verdict can mention it.
- **UI (Dutch):** in the Inkomen step beside Rentevaste periode, "Aangeboden rente met NHG (%)" and "Aangeboden rente zonder NHG (%)", entered as percentages, blank allowed. Hint: "Uit je offerte, voor de rentevaste periode hierboven. Leeg: marktrente van <datum>." Gevolgen, the Case's Betaalruimte and the Bid Advice "Hoe berekend" say "eigen rente x%" or "marktrente x% (<datum>)".
- **Export:** the Markdown export names the rate per route and its source. The own rate is rounded to 0,1 procentpunt (e.g. 4,23% → 4,2%); the market rate stays exact, as it is not household data. Applies with and without `profile=false`.
- **Out of scope:** an expiry date for the offerte; fetching rates automatically (DNB Statistics API, scraping); market rates per rentevaste periode.

### Acceptance criteria

- [ ] Buyer Profile and `FinanceDraft` accept `offered_rate_nhg` and `offered_rate_no_nhg`, both optional, validated within range; existing profiles load with both blank and unchanged figures
- [ ] Max mortgage and monthly cost use the own rate of a route when set, else the market snapshot, per route independently
- [ ] Under ten years fixed the test rate is still at least the AFM toetsrente, also with an own rate below it
- [ ] Changing an own rate marks Oordelen built on the old profile Achterhaald
- [ ] `reduce_profile` carries the rate used per route and its source
- [ ] Gevolgen, Betaalruimte and Hoe berekend show "eigen rente" or "marktrente (<datum>)" per route
- [ ] Export rounds the own rate to 0,1 procentpunt and names its source
- [ ] `GLOSSARY.md` Buyer Profile entry mentions the offered rates

### Tests

Seam: the HTTP API, as ticket 28.

- [ ] API: own NHG rate only changes the NHG route; own non-NHG rate only the other; both blank equals today's figures
- [ ] API: 5 years fixed with an own rate of 4% tests at 5%; 10 years fixed with 4% tests at 4%, against hand-computed max mortgages
- [ ] API: monthly cost at the own rate of the route taken
- [ ] API: saving a changed rate marks an existing Verdict Achterhaald
- [ ] API: reduced profile carries rate and source; export rounds the own rate
- [ ] E2E: enter both rates in the form, Gevolgen shows "eigen rente"

## Comments

Raised 2026-11-09: the rate was fixed at the 2026-11-02 snapshot. Ideal would be the rate of this exact moment, but no open source offers it: DNB's Statistics API gives monthly averages of new contracts with a one to two month lag, and daily figures exist only on comparison sites and bank pages without an API (scraping). The household's own offerte is the most accurate rate anyway, so this ticket adds that as an override; automatic fetching is left for later.

Decided with the user (2026-11-09): two fields (with and without NHG); the AFM toetsrente floor still applies under ten years fixed; a changed rate makes Oordelen Achterhaald; the rate may reach the LLM; the export rounds it; an offerte expiry date is out of scope.

Triaged (user, 2026-11-09): validation range 0,5% to 15%; the export rounds the own rate to 0,1 procentpunt. Ready for agent.
