# Funda Griller

Personal tool that takes a funda.nl purchase listing, assembles a complete evidence file on the house, and tells one household whether and how to bid. The UI is fully Dutch; each term below carries its Dutch UI label.

## Language

**Listing**:
A single koopwoning advertisement on funda.nl, with all its text, facts and images, as captured at one moment in time.
_Dutch UI_: **Woning** for the house in lists and navigation; **Advertentie** only where the captured snapshot is explicit (e.g. "advertentie van 12 maart")
_Avoid_: Ad, advert, property page

**Source**:
Any external place besides the Listing that supplies facts about a house or its surroundings (e.g. Kadaster, WOZ, energielabel register).
_Dutch UI_: **Bron**
_Avoid_: Provider, feed, integration

**Stale**:
Describes a fact whose fetch date is older than its Source's time-to-live. Stale facts stay in the Case and are marked as such; they are only refreshed when the user manually re-fetches.
_Dutch UI_: **Verouderd**
_Avoid_: Expired, outdated

**Out of date**:
Describes a Verdict or Case produced from an earlier Case, Buyer Profile or rule version than the current ones. Distinct from Stale, which is about the age of a single fact.
_Dutch UI_: **Achterhaald**
_Avoid_: Stale (for Verdicts and Cases), expired

**Case**:
The deterministic evidence file for one house: the Listing plus facts gathered from Sources, computed metrics, and the Flags raised from them. Contains no judgement.
_Dutch UI_: **Dossier**
_Avoid_: Report, profile

**Flag**:
A single noteworthy finding in a Case, classed as pro, con or risk, and traceable to the facts that triggered it.
_Dutch UI_: **Signaal**; the classes are **Pluspunt**, **Minpunt** and **Risico**
_Avoid_: Warning, issue, insight

**Observation**:
A fact in a Case that was extracted from Listing photos or floorplan by a vision model at ingestion (e.g. "kitchen looks 20+ years old") and stored, marked as estimated.
_Dutch UI_: **Waarneming** (marked **geschat**)
_Avoid_: Image analysis result, detection

**Document**:
A file supplied by the selling agent or seller and uploaded by the user against a Listing, such as the Vragenlijst (seller questionnaire), Lijst van zaken (inventory of what stays), or other papers.
_Dutch UI_: **Document**
_Avoid_: Attachment, upload, paperwork

**Finding**:
A fact extracted from a Document at upload time and stored in the Case with its page reference, marked as seller-stated rather than verified.
_Dutch UI_: **Bevinding** (marked **door verkoper**)
_Avoid_: Claim, extraction

**Verdict**:
The LLM's rating of a Case against the Buyer Profile, as one of four tiers (Must buy, Consider, Skip, Hard no), with reasoning.
_Dutch UI_: **Oordeel**; the tiers are **Zeker kopen**, **Overwegen**, **Overslaan** and **Harde afwijzing**
_Avoid_: Score, grade, recommendation

**Hard no**:
The Verdict tier forced deterministically when the Case hits a deal-breaker from the Buyer Profile, before the LLM rates. A price deal-breaker ("te duur", "boven budget") only forces it when the Expected Sale Price is strongly grounded (comparables), not on a WOZ estimate; there the Flag stays a con for the model to weigh.
_Dutch UI_: **Harde afwijzing**
_Avoid_: Reject, blocked

**Bid Advice**:
Guidance accompanying a Verdict on how to bid: an opening bid, a walk-away maximum, and suggested conditions. The opening bid is the model's, kept within a narrow band around the Guide Bid.
_Dutch UI_: **Biedadvies**; its parts are **Openingsbod**, **Maximumbod** and **Voorwaarden**
_Avoid_: Bid strategy, offer

**Guide Bid**:
The opening bid the Case derives deterministically, before the model sees it: the Expected Sale Price less a discount that follows from how the seller priced the house and how long it has been on the market, never above the asking price or the Walk-away Maximum, rounded down. The model may adjust it within a band and must explain any deviation. Absent when there is no Walk-away Maximum, and for a house sold under reservation.
_Dutch UI_: **Richtbod**; shown next to the Openingsbod only when they differ
_Avoid_: Calculated bid, baseline bid, target bid

**Walk-away Maximum**:
The highest price at which the house still makes sense, derived by the Verdict service (never proposed by the model): the lower of the household's affordable maximum and the Expected Sale Price less the Renovation Estimate's Direct nodig midpoint, plus a configured premium (5%). The affordable maximum is the highest price a lender would finance under the Dutch lending norms for the year of the expected levering: the mortgage may not exceed the price, so kosten koper and the same Direct nodig midpoint come from the household's own funds and home equity. The Expected Sale Price is its only price basis, so it is weakly grounded exactly when the Expected Sale Price is (the Bid Advice says so plainly); without an Expected Sale Price there is no Walk-away Maximum, not even an affordability-only one, and no opening bid.
_Dutch UI_: **Maximumbod**
_Avoid_: Max price, ceiling

**Renovation Estimate**:
What the house may cost to renovate, in the Case: items priced as low–high ranges from a versioned cost table of public average prices, each triggered by Case facts (Observations, Findings, the energielabel, the build year) and citing them, marked estimated. Split into three urgency classes. The same for every Buyer Profile; its Direct nodig midpoint lowers the affordable maximum and the Walk-away Maximum.
_Dutch UI_: **Verbouwingsraming** (shown as **Verbouwingskosten**); the classes are **Direct nodig**, **Binnen 5 jaar** and **Optioneel**
_Avoid_: Renovation budget, quote, cost to fix

**Comparable**:
A nearby Listing that funda offers as recently sold or recently listed next to a house, fetched only on the user's request and capped in number. Its price is its (last) asking price, not a registered sale price: the average overbid for the soort woning is added to it before it feeds the Expected Sale Price. Only comparables of the same kind count (an apartment is no comparable for a house), and only those of the same soort woning when there are enough of them. Too few comparables are **thin** and do not ground the Expected Sale Price (or the Walk-away Maximum).
_Dutch UI_: **Vergelijkbare woning**; the metric is **t.o.v. vergelijkbaar**; thin is **Dun**
_Avoid_: Comps, similar listing, reference house

**Expected Sale Price**:
What the house is expected to sell for, derived in the Case from evidence independent of its own asking price: sufficient comparables plus the average overbid for the soort woning (strongly grounded), else the WOZ value brought to today's prices (weakly grounded), else none. Never the asking price. Carries a low-high range (the interquartile range of the comparables) on the comparables basis.
_Dutch UI_: **Verwachte verkoopprijs**; weak is **Zwak onderbouwd**
_Avoid_: Market value, valuation, taxatie, realistic price

**Prijsstelling**:
How the seller priced the house against its Expected Sale Price: **hoog ingezet** (asking price more than the configured band, default 5%, above), **marktconform** (within the band) or **laag ingezet** (below it). Information only: not a Flag, never counted against the house. Absent when there is no asking price or no Expected Sale Price.
_Dutch UI_: **Prijsstelling**
_Avoid_: Overpriced, underpriced

**Expected levering**:
The date a bid made today is expected to transfer at the notary (today plus a configured number of months). The year's lending norms, the starters' ages and the startersvrijstelling limit are taken at this date, not today.
_Dutch UI_: **levering** (as in "levering rond februari 2027")
_Avoid_: Closing date, transfer date

**Buyer Profile**:
The household's finances (income, household composition, assets, current home equity, rentevaste periode, the mortgage rate offered to them with and without NHG (optional; blank, the market snapshot in the affordability rules applies to that route), debts by kind, whether each adult has used the startersvrijstelling) and preferences (must-haves, nice-to-haves, deal-breakers, commute destinations). Entered manually and stored locally. Each debt has a kind and the figures that kind needs: a study loan its debt, rate and terugbetaalregels (SF35 or SF15, optionally the Mijn DUO amount), a revolving credit its limit, an instalment loan or private lease its monthly term, any other loan its monthly amount. The debts never reach the LLM.
_Dutch UI_: **Koperprofiel**; the preference lists keep their English labels **Must-have**, **Nice-to-have** and **Deal-breaker**, which are common usage in Dutch. Debts are **Schulden**, the kinds **Studieschuld**, **Doorlopend krediet**, **Aflopend krediet**, **Private lease** and **Andere lening**
_Avoid_: User profile, account, settings

**Toetslast**:
What one debt counts for a month in the maximum mortgage, before the Trhk gross-up: a study loan's wettelijk maandbedrag, 2% of a revolving credit's limit, an instalment loan's or private lease's monthly term. Each kind's rule is a versioned rule in `config/affordability.toml`. What a debt costs in **leenruimte** is how much higher the maximum mortgage would be without it.
_Dutch UI_: **toetslast**; the cost is "kost € … leenruimte"
_Avoid_: Debt payment, monthly debt (for the weighed figure)
