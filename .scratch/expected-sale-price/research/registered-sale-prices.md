# Registered sale prices: which source can ground the Expected Sale Price?

Researched 2026-11-17 for ticket 06. Context: ADR-0004 bases the Expected Sale Price on comparables' **asking** prices plus the average overbid; ADR-0002 accepts pyfunda for a personal, low-volume, user-triggered tool. Claims carry their source. **UNVERIFIED** marks what I could not confirm from a primary source.

## Summary

| Source | What | Granularity | Cost | Terms / automation | Lag |
|---|---|---|---|---|---|
| Kadaster Koopsominformatie (webshop) | Exact koopsom, sale date, plot size, house number | One 6-char postcode, all private purchases since 2003 | €3,70 per postcode | Manual order, e-mail download link; non-exclusive, non-transferable use | Monthly refresh around the 20th, after the deed is registered |
| Kadaster KOOPSOM by SMS | Exact koopsom of one address | One address | €1,50, only charged if data exists | Manual SMS to 8118 | Same |
| Kadaster Woningrapport | Includes recent sale prices of comparable homes nearby (Kadaster data) | One address plus neighbours | €21,50 | Manual webshop order | Same |
| funda "verkocht" via pyfunda | **Last asking price** plus sale date. No sale price | Per listing | Free | Funda ToS forbids automated collection (ADR-0002) | Live |
| Walter Living free lookup (pyfunda `price_history`) | Asking-price history plus a "Verkocht" badge on the **asking** price, and WOZ | Per listing | Free | Undocumented endpoint | Live |
| Walter Plus | "Nationwide sale prices on every home" (Kadaster feed) | Per address, in their UI | €29/month | No API | Monthly Kadaster feed |
| Huispedia Plus | Sale prices of sold homes in the neighbourhood | In their UI | €49/month | No consumer API found | Unknown |
| Brainbay (NVM) | Transaction data of NVM and non-NVM agents | For NVM members and business partners | Not public | No consumer product found | n/a |
| CBS StatLine 83625NED | **Average** sale price of existing homes | Gemeente/year | Free | Reuse with source credit | Yearly |
| CBS microdata | Koopsom plus postcode4 | Per transaction | Paid remote access | Requires Kadaster permission | n/a |
| WOZ-waardeloket | WOZ value, not sale price | Per address | Free | Already used indirectly via Walter | Yearly |

## 1. Kadaster

### Koopsominformatie (per postcode, or per address by SMS)
Source: https://www.kadaster.nl/producten/woning/koopsominformatie
- Content: for one postcode area (example "1234AB", so a six-character postcode), every house and apartment bought **by private persons after 1 January 2003**. Per sale: house number, sale date, **koopsom** and plot area (not for apartments). No living area and no house type.
- Price: webshop **€3,70** (the page does not say whether VAT is included). SMS `KOOPSOM <postcode> <huisnummer> <toevoeging>` to 8118 returns the koopsom of one address for **€1,50**, charged only if data exists.
- Delivery: webshop sends an e-mail with a download link (the product sample is a PDF; delivery format not stated explicitly). SMS answers directly.
- Gaps: no koopsom when the deed lacks postcode and house number, for former rental homes, land-only purchases, parcels split after transfer, non-sale transfers (inheritance, divorce), or prices under €5.000 or over €5.000.000.
- Lag: the price is known once the notarial deed is registered. Data is refreshed monthly; the previous month is usually available around the 20th. The most recent sale may be missing. A sale agreed on funda is typically transferred at the notary weeks to months later, so a "recently sold" comparable is often **not yet** in Kadaster (general knowledge of the Dutch transfer process, **UNVERIFIED** in a Kadaster source).
- Coverage: all Kadaster-registered private purchases, nationwide. This is the register itself, so it is the most authoritative source.

### Woningrapport
Source: https://www.kadaster.nl/producten/woning/woningrapport
- Owner, maps, build year, area, energy label, an estimated value, and **recent sale prices of comparable homes nearby** from Kadaster Koopsominformatie, plus regional price trends.
- **€21,50**, webshop only (iDEAL|Wero or credit card), e-mail download link. Same lag and gaps as above.
- How many comparables and how they are selected is not stated (**UNVERIFIED**).

### Terms
Source: https://www.kadaster.nl/about-us/general-terms-of-delivery
- Art. 6.1: non-exclusive, non-transferable right of use. Art. 6.2: use only for the agreed purpose; supplying to third parties needs express conditions. Art. 6.5: may be replicated **for use within the customer's own application** and for backup. Art. 6.3: personal data may not be used in derived products for commercial purposes. Art. 8.1: Kadaster keeps copyright and database right.
- Nothing on automated retrieval; the webshop and SMS are manual purchase flows. Storing a bought koopsom file in a personal, non-shared app fits art. 6.5. Republishing does not.

### Business access and open data
- No Kadaster API for koopsommen to consumers was found. A 2010 tariff amendment priced single koopsommen at €1,25 (https://zoek.officielebekendmakingen.nl/stcrt-2010-2113.pdf); current business tariffs are not public in what I could fetch (**UNVERIFIED**).
- Kadaster koopsommen are **not open data**. The CBS microdata file with koopsom and postcode4 may only be used with prior Kadaster permission and holds only market-conform transactions (https://www.cbs.nl/-/media/cbs-op-maat/microdatabestanden/documents/2025/18/transactieskoopwoningen.pdf). The municipality of Amsterdam notes it may not pass on Kadaster transactions per address (https://ckan.bertha.geodan.nl/dataset/amsterdam-open-geodata-472-woningwaarde-2022).
- Reseller kadastralekaart.com sells koopsommen per item in API bundles (Business tier €199/month per search snippet of https://kadastralekaart.com/api); the page returned 403 to me, so prices and whether individuals may subscribe are **UNVERIFIED**. Too costly for one household anyway.

## 2. funda "verkocht" via pyfunda (installed pyfunda 3.1.5)

Package source: `backend/.venv/lib/python3.13/site-packages/funda/`.
- `Funda.listing()` parses `Price.NumericSellingPrice` (`_detail_parser.py:108`) and `SalesHistory` rows (`_detail_parser.py:329`, `listing.py:249`, with a `sale_date` property reading "Verkoopdatum"). There is no field for a sale price.
- `Funda.search(category="sold")` filters on availability `unavailable` and returns `price.selling_price` (`search.py`, `_search_parser.py:115`): the listing's asking price.
- `Funda.price_history()` posts to Walter Living's `api.walterliving.com/hunter/lookup` (`funda.py:263`, `constants.py:14`); its parser maps statuses "Vraagprijs", "Verkocht" and "WOZ" (`_price_history_parser.py`).

One real call (2026-11-17) on a sold comparable already stored by the app (global id 8062607, status "Verkocht"), one detail request and one Walter lookup:
- Detail: `Price = {"SellingPrice": "€ 425.000 k.k.", "NumericSellingPrice": 425000}`, `IsSoldOrRented: true`, `SalesHistory` rows "Aangeboden sinds 27 juni 2026", "Verkoopdatum 16 juli 2026", "Looptijd 2 weken". No sale price.
- Walter: three changes, all €425.000 from source "Funda" with badges "Vraagprijs", "Onder bod", "Verkocht", parsed as `asking_price`; then the WOZ series. The "Verkocht" entry repeats the last **asking** price.

**Conclusion: pyfunda and the funda mobile API expose only the last asking price and the sale date (and time on the market) of sold listings, not the sale price.** The sale date and looptijd are still useful: they tell which comparables should by now be in the Kadaster register, and they can feed the tempo signal.

## 3. Other sources

- **Walter Living.** Gets "all transactions in the Netherlands every month" via a Kadaster partnership (https://walterliving.com/help/kadaster). Walter Plus, €29/month, promises "nationwide sale prices on every home"; Walter Sessions €149 includes "real transaction data for your home" (https://walterliving.com/nl/en/pricing). No public API; its free lookup gives asking prices only (probe above). Terms on automated access not found (**UNVERIFIED**); scripting the paid UI would go beyond what ADR-0002 accepted.
- **Huispedia.** Huispedia Plus €49/month shows sale prices of recently sold comparable homes on a map; the data sources are not named (search snippets of https://huispedia.nl/huispedia-plus, page itself returned 403, **UNVERIFIED**). Huispedia has API terms (https://huispedia.nl/api-voorwaarden, 403 to me) and a business tier Huispedia Pro €99/month per adviser with a yearly contract. Not a fit.
- **Brainbay / NVM.** Brainbay builds data products for NVM members from data of members and non-members (https://brainbay.nl/, https://www.liza.nl/en/71551034/brainbay). No consumer product or public pricing found. Access via an NVM agent only.
- **CBS StatLine.** Table 83625NED: average sale price of existing homes bought by private persons, from Kadaster transactions, per gemeente, yearly 1995-2025, last modified 2026-02-17; reuse allowed with source credit (https://opendata.cbs.nl/ODataApi/odata/83625NED/TableInfos). Price indices per region (85792NED, CC-BY 4.0, quarterly; https://www.cbs.nl/nl-nl/cijfers/detail/85792NED). Area averages only: useless as a per-house basis, but a free way to **index** an older koopsom to today.
- **WOZ-waardeloket.** WOZ values per address (already in the Case via Walter). Not a sale price. Rijksoverheid points to paid Kadaster koopsominformatie for actual prices (https://www.rijksoverheid.nl/documenten/vraag-en-antwoord/waardering-onroerende-zaken-woz/woz-waarde-controleren).

## Recommendation

**Kadaster Koopsominformatie becomes the strongest Expected Sale Price basis**, bought manually by the household and imported into the app. It is the register itself, exact per address, cheap (€3,70 per postcode or €1,50 per address), legally clean for personal use in one's own application (terms art. 6.5), and nationwide. No other source gives exact sale prices at a household's cost and terms: funda and the free Walter lookup only give asking prices, Walter Plus and Huispedia Plus are closed UIs, Brainbay is for agents, CBS is area averages.

What it takes:
1. **Acquisition stays manual.** No API exists for consumers; do not script the webshop or SMS. The user buys the postcode file(s) for the house's postcode and neighbouring postcodes (typically a few, so roughly €4–€20 per house), or texts KOOPSOM for specific comparable addresses.
2. **Import.** A new Source, e.g. `registered_sales` with provenance "Kadaster koopsominformatie", fed by uploading the Kadaster download (parse the PDF, format to confirm on a first purchase) or by manual entry per address (postcode, number, date, koopsom).
3. **Enrich.** Kadaster gives no living area or house type. Join each address to BAG (open via PDOK; the app already calls the PDOK locatieserver) for living area and use, and to funda comparables where the same address appears (house type).
4. **Index.** Bring each koopsom to today with the CBS regional price index (85792NED, free), so older sales count.
5. **Case rule.** Sufficient registered sales of the same kind → median indexed €/m² × living area, with **no overbid correction**; strongest basis, ahead of comparables plus overbid, then WOZ. This changes ADR-0004's basis order and needs an ADR amendment and a new ticket.
6. **Know the lag.** Sales from the last few months will be missing; funda's sale date tells which comparables to expect in the register yet. Recent asking-price comparables remain the freshest evidence, so they stay a fallback.

Cheapest trial before building: buy one €3,70 postcode file for a current Listing to confirm the delivery format and how many usable sales a postcode yields.
