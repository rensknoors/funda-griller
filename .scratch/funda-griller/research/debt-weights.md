# Debt weights for the maximum mortgage (ticket 30)

Researched 2026-11-09, primary sources first. Every claim has its source next to it. A weight no primary source confirms is marked **UNVERIFIED** and goes into `config/affordability.toml` marked the same way.

Context: the Buyer Profile records debts by kind (`study_loan`, `revolving_credit`, `instalment_loan`, `private_lease`, `other`). Each becomes a monthly toetslast that comes off the allowed monthly cost (financieringslast) before it is turned into a mortgage.

## 1. Trhk: how other obligations come off (verified)

Source: Tijdelijke regeling hypothecair krediet, https://wetten.overheid.nl/BWBR0032503, version in force from 2026-01-01 (read 2026-11-09).

- **Art. 3 lid 12:** other financial obligations of the consumer are either added to the financieringslast or deducted from the toegestane financieringslast. The Trhk does not say how each kind is weighed; that is left to the lender (and the GHF, below).
- **Art. 3a lid 1:** for a studielening the lender counts the termijnbedrag the consumer owes for interest and repayment.
- **Art. 3a lid 2:** when the mortgage interest is deductible, that monthly amount is multiplied by a factor per toetsrente column (1,05 up to 2,000% rising to 1,40 from 6,001%). This is the existing `debt_gross_up` table; unchanged for 2027 (Nibud advies 2027 tabel 8, as cited in ticket 28).
- **Art. 3a lid 3:** when the consumer owes nothing yet (still studying, aanloopfase), owes nothing in an aflosvrije periode, or owes a lowered amount after a draagkrachtmeting, the lender may instead work from the actual restschuld, the actual rate and the remaining term. So the toetslast is never the lowered draagkracht amount and never €0: it is the full annuity on the debt.

## 2. DUO: the wettelijk maandbedrag (verified)

Source: DUO, "Berekening maandbedrag", https://duo.nl/particulier/studieschuld-terugbetalen/berekening-maandbedrag.jsp, and "Zo werkt terugbetalen", https://duo.nl/particulier/studieschuld-terugbetalen/zo-werkt-terugbetalen.jsp (read 2026-11-09).

- DUO first works out the monthly amount that repays the debt and its interest within the term: the wettelijk maandbedrag. The term is 15 or 35 years by terugbetalingsregels (SF15: 180 months; SF35: 420 months).
- A lower draagkracht lowers what is paid, not the wettelijk maandbedrag.
- Aanloopfase: two years from 1 January after studiefinanciering stops, nothing to repay, interest runs on.
- Aflosvrije periode: up to 60 months, extends the term.
- Not stated on the page: the annuity formula itself. The code uses the standard monthly annuity (`debt × r / (1 − (1 + r)^−n)`, `r` = yearly rate / 12), which the household can override with the amount on Mijn DUO (triage: keep the override).

## 3. NVB Gedragscode Hypothecaire Financieringen (verified for consumptief krediet)

Source: Gedragscode Hypothecaire Financieringen, in force 2020-08-01 (art. 12), NVB and Verbond van Verzekeraars, https://www.verzekeraars.nl/media/7585/gedragscode-hypothecaire-financieringen-2020.pdf (the NVB copy at nvb.nl/media/3402 returns 404). No later version found (search 2026-11-09; vanbruggen.nl begrippenlijst also names 2020-08-01 as current).

Paragraph 4 "Leencapaciteit", lid 5 (quoted):

> Als aan de consument een consumptief krediet is verstrekt, houdt de hypothecair financier rekening met de daaraan verbonden financiële lasten in die zin dat hij per maand ten minste 2% van de kredietlimiet bij doorlopend krediet of ten minste de contractuele rente en aflossing van de oorspronkelijke kredietsom tot einddatum bij aflopend krediet, in aanmerking zal nemen als financiële lasten.

- **Doorlopend krediet / creditcard:** 2% of the kredietlimiet per month, drawn or not. Verified.
- **Aflopend krediet:** at least the contractual interest and repayment of the original sum until the end date: the contractual monthly term. Verified. A percentage of the original amount is not what the code prescribes, so the original amount is not asked for.
- Exception: not counted when repaid from own funds and ended at the latest on the day the mortgage is given. Out of scope (the household leaves such a debt out).
- The GHF does not mention private lease or study loans.

## 4. Private lease (weight UNVERIFIED)

- **BKR** (https://www.mijnkredietregistratie.nl/nl/mijn-situatie/private-autolease, read 2026-11-09): a lease contract with a company in the Keurmerk Private Lease is registered as a krediet; new contracts at 100% of the total amount, contracts from before 2022-04-01 at 65%.
- No primary source (Trhk, GHF, Nibud) states the share of the monthly lease term a lender counts. Secondary sources (Van Bruggen 2021, Hypotheker) say lenders count the full term since the 2022-04-01 registration change. Config: **100% of the monthly lease term, UNVERIFIED**.
- A pre-2022 contract registered at 65% may be counted lower by a lender; not modelled (the conservative full term is used).

## 5. Gross-up for kinds other than a study loan (Nibud advice, not law)

Source: Nibud, Advies hypotheeknormen 2026 (September 2025), hoofdstuk 8 "Persoonlijke financiële verplichtingen", https://zoek.officielebekendmakingen.nl/blg-1221422.pdf, pp. 41–42 and 74–75.

- The Trhk prescribes the gross-up only for study loans. Nibud advises grossing up every non-deductible obligation (consumptief krediet, private lease) so that no obligation is favoured, and notes that lenders often do not. Ticket 28 cited the same advice in advies 2027 §5.2.
- Config keeps the gross-up on for every kind (as today for `other_monthly_debt`), so the figure is prudent; a lender that does not gross up consumer credit will lend somewhat more. Each kind's `gross_up` is a switch in config.

## Summary for config

| Kind | Monthly toetslast | Gross-up | Source | Status |
|---|---|---|---|---|
| study_loan | annuity on debt at DUO rate, 420 (SF35) or 180 (SF15) months; Mijn DUO override | yes | Trhk art. 3a; DUO | verified |
| revolving_credit | 2% of the limit | yes (Nibud) | GHF 2020 §4 lid 5 | verified |
| instalment_loan | contractual monthly term | yes (Nibud) | GHF 2020 §4 lid 5 | verified |
| private_lease | 100% of the monthly lease term | yes (Nibud) | BKR registration only | **UNVERIFIED** |
| other | the monthly amount | yes (Nibud) | Nibud advies 2027 §5.2 | as before |
