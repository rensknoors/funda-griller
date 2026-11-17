# 01: Own renovation plans per house

**Type:** task

**Blocked by:** none

**Status:** needs-triage

## What the user wants

Per house, the household enters what they still want or need to change themselves (e.g. "keuken vervangen", "badkamer", "dakkapel", "vloer"), with an amount. Today the only renovation figure is the **Renovation Estimate**: deterministic, from a cost table, the same for every Buyer Profile, and only its **Direct nodig** midpoint lowers the affordable maximum and the **Walk-away Maximum**. The household's own plans, which can differ a lot from the estimate, are not counted anywhere.

Motivation (2026-11-17): the Walk-away Maximum is the Expected Sale Price less Direct nodig, plus 5%. What the household will spend on the house after buying should weigh in the same way, so the Maximumbod and the Openingsbod reflect the house they will actually live in.

## Rough shape (to be settled in triage)

- A list per house: description, amount (or low–high), and whether it is a must (before moving in / required) or a wish.
- Musts lower the affordable maximum and the Walk-away Maximum like Direct nodig does (paid from own funds and home equity), without counting an item twice when the Renovation Estimate already has it.
- Wishes are shown in the Biedadvies and the Dossier, but do not lower the Maximumbod.
- Belongs to the household, not to the Case: the Case stays the same for every Buyer Profile (ADR-0001). A change makes the Verdict **Achterhaald**.
- Dutch UI, with a new glossary term once the concept is settled (e.g. **Verbouwplan**).

## Open questions

- Must vs wish: is that split right, and do only musts lower the Maximumbod?
- Overlap with the Renovation Estimate: does an own item replace the matching estimate item (e.g. own "keuken € 25.000" replaces the estimated kitchen), or are both shown and the user chooses?
- Financing: may part of it be financed (bouwdepot, the extra room for energiebesparende voorzieningen), or does it always come from own funds as Direct nodig does today?
- Does the model see the plans (and weigh them against `renovation_tolerance`), or do only the amounts count?
- Entry: free text plus amount, or pick from the cost table's items with their price range as a suggestion?
- Export: are the plans in the Markdown export, or kept private like the debts?

## Comments
