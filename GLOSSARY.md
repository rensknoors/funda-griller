# Funda Griller

Personal tool that takes a funda.nl purchase listing, assembles a complete evidence file on the house, and tells one household whether and how to bid.

## Language

**Listing**:
A single koopwoning advertisement on funda.nl, with all its text, facts and images, as captured at one moment in time.
_Avoid_: Ad, advert, property page

**Source**:
Any external place besides the Listing that supplies facts about a house or its surroundings (e.g. Kadaster, WOZ, energielabel register).
_Avoid_: Provider, feed, integration

**Stale**:
Describes a fact whose fetch date is older than its Source's time-to-live. Stale facts stay in the Case and are marked as such; they are only refreshed when the user manually re-fetches.
_Avoid_: Expired, outdated

**Case**:
The deterministic evidence file for one house: the Listing plus facts gathered from Sources, computed metrics, and the Flags raised from them. Contains no judgement.
_Avoid_: Report, dossier, profile

**Flag**:
A single noteworthy finding in a Case, classed as pro, con or risk, and traceable to the facts that triggered it.
_Avoid_: Warning, issue, insight

**Observation**:
A fact in a Case that was extracted from Listing photos or floorplan by a vision model at ingestion (e.g. "kitchen looks 20+ years old") and stored, marked as estimated.
_Avoid_: Image analysis result, detection

**Document**:
A file supplied by the selling agent or seller and uploaded by the user against a Listing, such as the Vragenlijst (seller questionnaire), Lijst van zaken (inventory of what stays), or other papers.
_Avoid_: Attachment, upload, paperwork

**Finding**:
A fact extracted from a Document at upload time and stored in the Case with its page reference, marked as seller-stated rather than verified.
_Avoid_: Claim, extraction

**Verdict**:
The LLM's rating of a Case against the Buyer Profile, as one of four tiers (Must buy, Consider, Skip, Hard no), with reasoning.
_Avoid_: Score, grade, recommendation

**Hard no**:
The Verdict tier forced deterministically when the Case hits a deal-breaker from the Buyer Profile, before the LLM rates.
_Avoid_: Reject, blocked

**Bid Advice**:
Guidance accompanying a Verdict on how to bid: an opening bid, a walk-away maximum, and suggested conditions.
_Avoid_: Bid strategy, offer

**Walk-away Maximum**:
The highest price at which the house still makes sense, derived from comparable sales and the household's affordability.
_Avoid_: Max price, ceiling

**Buyer Profile**:
The household's finances (income, household composition, assets, current home equity) and preferences (must-haves, nice-to-haves, deal-breakers, commute destinations). Entered manually and stored locally.
_Avoid_: User profile, account, settings
