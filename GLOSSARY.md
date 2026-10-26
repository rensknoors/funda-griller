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
The Verdict tier forced deterministically when the Case hits a deal-breaker from the Buyer Profile, before the LLM rates.
_Dutch UI_: **Harde afwijzing**
_Avoid_: Reject, blocked

**Bid Advice**:
Guidance accompanying a Verdict on how to bid: an opening bid, a walk-away maximum, and suggested conditions.
_Dutch UI_: **Biedadvies**; its parts are **Openingsbod**, **Maximumbod** and **Voorwaarden**
_Avoid_: Bid strategy, offer

**Walk-away Maximum**:
The highest price at which the house still makes sense, derived by the Verdict service (never proposed by the model): the lower of the household's affordable maximum and what sufficient comparables put the house at plus a configured premium. With thin or missing comparables it rests on the asking price plus a configured margin instead, and the Bid Advice says plainly that it is weakly grounded. With neither sufficient comparables nor an asking price it is the affordable maximum alone, also weakly grounded.
_Dutch UI_: **Maximumbod**
_Avoid_: Max price, ceiling

**Comparable**:
A nearby Listing that funda offers as recently sold or recently listed next to a house, fetched only on the user's request and capped in number. Its price is its (last) asking price, not a registered sale price. Too few comparables are **thin** and do not ground the Walk-away Maximum.
_Dutch UI_: **Vergelijkbare woning**; the metric is **t.o.v. vergelijkbaar**; thin is **Dun**
_Avoid_: Comps, similar listing, reference house

**Buyer Profile**:
The household's finances (income, household composition, assets, current home equity) and preferences (must-haves, nice-to-haves, deal-breakers, commute destinations). Entered manually and stored locally.
_Dutch UI_: **Koperprofiel**; the preference lists keep their English labels **Must-have**, **Nice-to-have** and **Deal-breaker**, which are common usage in Dutch
_Avoid_: User profile, account, settings
