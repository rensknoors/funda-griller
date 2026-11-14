# 30: Debts by kind (studieschuld, private lease, other loans)

**What to build:** The Buyer Profile records debt as one number, `other_monthly_debt`, and the max mortgage weighs all of it as a DUO study loan. Lenders weigh each kind of debt differently: a study loan by its wettelijk maandbedrag, a doorlopend krediet by its limit even when unused, a private lease by its lease term. Let the household enter each debt by kind and weigh each one the way the norms say, so the maximum mortgage and the affordable maximum are right for households with debt. Decision support, not advice: every weighing rule cites its source and check date in `config/affordability.toml`.

**Blocked by:** none

**Status:** resolved

### Current state

- `other_monthly_debt` (`backend/app/buyer_profile.py:99`, form hint at `frontend/src/BuyerProfileForm.tsx:267`) is one monthly sum: "Studieschuld (DUO-maandbedrag), autolening, private lease".
- `_norm` (`backend/app/affordability.py:180`) multiplies the whole sum by the `debt_gross_up` factor of Trhk art. 3a lid 2. That article covers DUO study loans; Nibud (advies 2027 §5.2) advises the same for other non-deductible loans, but lenders follow the Gedragscode Hypothecaire Financieringen for consumer credit and lease.
- What goes wrong:
  - **Studieschuld:** the household has to work out the right monthly amount. Lenders use the wettelijk maandbedrag from the original debt and rate (35 or 15 years, by stelsel), not the lower draagkracht amount, not €0 during the aanloopfase, and not 0 when the debt is still being built up. Entering the actual DUO payment lowers the weight too far.
  - **Doorlopend krediet / credit card:** a lender counts a percentage of the limit per month (2% per the Gedragscode, to verify), whether or not anything is drawn. The household has no field for a limit.
  - **Private lease:** registered at BKR since 2021 and counted from the monthly lease term (at what share, to verify against the Gedragscode as now in force). Now it is entered as a sum alongside the rest with no distinction.
  - **Aflopend krediet (car loan, personal loan):** the monthly term, or a percentage of the original amount, whichever the Gedragscode prescribes.
- None of this reaches the Gevolgen panel as a line: the household cannot see what each debt costs them in mortgage.

### Design

- **Rule tables (per year, `config/affordability.toml`):** a `debts` section per year with, per kind, how it becomes a monthly toetslast and whether the `debt_gross_up` applies. Each rule cites a primary source (Trhk, NVB Gedragscode Hypothecaire Financieringen, DUO, Nibud advies) with check date. Anything not verified is marked as such in the header. Bump the rule table `version`.
- **Buyer Profile (finances):** replace `other_monthly_debt` with a list `debts`, each entry with a `kind` and the fields that kind needs:
  - `study_loan`: original debt (or debt now when still studying), interest rate, `stelsel` (SF35 / SF15). The code derives the wettelijk maandbedrag; the household may override it with the amount on Mijn DUO.
  - `revolving_credit` (doorlopend krediet, credit card): credit limit.
  - `instalment_loan` (aflopend krediet): monthly term and original amount.
  - `private_lease`: monthly lease term.
  - `other`: a monthly amount, weighed as now.
  - Migration: an existing `other_monthly_debt > 0` becomes one `other` entry with that amount, so figures do not move until the household splits it. Profile version bumps, so existing Oordelen show **Achterhaald** only where the figures change.
  - Shown in the Gevolgen panel; none of it reaches the LLM (`reduce_profile` unchanged).
- **Affordability:** `_norm` sums the toetslast of every debt, by kind, instead of one gross-up on one number. The Gevolgen panel and the Dossier show, per debt, how much maximum mortgage it costs ("Studieschuld kost € 38.000 leenruimte").
- **UI (Dutch):** a repeatable "Schulden" vak in the Inkomen step, kind first, then its fields, with a hint per kind on where to find the figure (Mijn DUO, BKR-overzicht, leasecontract). Empty list is "geen schulden".
- **Export:** the Markdown export lists debts by kind with their toetslast; amounts follow the existing privacy rules of the export.

### Acceptance criteria

- [x] `affordability.toml` has a sourced `debts` section for 2026 and 2027; each rule cites a primary source and check date, or is marked UNVERIFIED
- [x] A study loan weighs by its wettelijk maandbedrag (from original debt, rate and stelsel), times the `debt_gross_up` factor of the toetsrente column, also during the aanloopfase
- [x] A revolving credit limit lowers the max mortgage even when nothing is drawn
- [x] A private lease lowers the max mortgage by its lease term at the Gedragscode weight
- [x] An instalment loan weighs per the Gedragscode
- [x] An existing profile with `other_monthly_debt` migrates to one `other` debt with unchanged figures
- [x] The Gevolgen panel shows, per debt, the leenruimte it costs
- [x] Rule table and profile versions bumped; Oordelen built on the old figures show Achterhaald
- [x] `GLOSSARY.md` updated (Buyer Profile, a term for a debt's toetslast if one is needed)

### Tests

Seam: the HTTP API, as ticket 28.

- [x] API: study loan of €30.000 at a given rate, SF35 and SF15, against a hand-computed wettelijk maandbedrag and the resulting max mortgage (at 5 and 10 years fixed)
- [x] API: revolving credit with a €5.000 limit and nothing drawn lowers the max mortgage
- [x] API: private lease and instalment loan against hand-computed examples
- [x] API: several debts together equal the sum of their separate effects
- [x] API: a profile stored with `other_monthly_debt` reads back as one `other` debt; Buyer Profile validates each kind's fields

## Comments

Raised 2026-11-09: debts (studieschuld, private lease, other loans) were not weighed properly. Ticket 28 added one `other_monthly_debt` field with the DUO gross-up for everything; this ticket splits it by kind.

Open questions for triage:

- Gedragscode weights (doorlopend krediet 2% of limit, private lease share, aflopend krediet) need a check against the current NVB Gedragscode text before they go into config.
- Alimentatie for an ex-partner: lenders subtract it from income. In scope here, or a separate ticket?
- Is a DUO override worth it, or should only the derived wettelijk maandbedrag count (as the lender will)?

Triage 2026-11-09 (user), resolving the open questions:

- Check the weights against primary sources first: the current NVB Gedragscode Hypothecaire Financieringen for doorlopend krediet, private lease and aflopend krediet; DUO for the wettelijk maandbedrag for SF35/SF15; the Trhk. Notes go in `.scratch/funda-griller/research/`. A weight that cannot be confirmed from a primary source goes into config marked UNVERIFIED.
- Alimentatie is out of scope.
- Keep the Mijn DUO override.

Resolved 2026-11-10. Research notes: `.scratch/funda-griller/research/debt-weights.md`. Rule table version 3.

- Verified: study loan (Trhk art. 3a lid 1–3; DUO 35/15 years), doorlopend krediet 2% of the limit and aflopend krediet at the contractual monthly term (Gedragscode Hypothecaire Financieringen 2020, §4 lid 5, in force 2020-08-01; no later version found).
- UNVERIFIED: private lease at 100% of the monthly lease term. The Gedragscode does not mention lease; BKR registers new contracts (from 2022-04-01) at 100%. So the "Gedragscode weight" criterion is met by the configured, UNVERIFIED weight.
- Decided in build: the instalment loan asks only for its monthly term. The Gedragscode prescribes the contractual term, so an original amount would go unused. The gross-up stays on for every kind (Nibud advice; the Trhk prescribes it only for study loans); each kind has a `gross_up` switch in config.
- What a debt costs is the maximum mortgage without that debt less the maximum with every debt. Shown in Gevolgen, as a note under Maximale hypotheek in the Dossier, and in the export (toetslast rounded to €50, cost to €5.000; left out without the profile).
- Stored profiles are not rewritten: an `other_monthly_debt` is migrated on read (API, Case, export). Figures do not move. The rule table version bump marks existing Oordelen Achterhaald; a saved split bumps the profile version as any save does.
