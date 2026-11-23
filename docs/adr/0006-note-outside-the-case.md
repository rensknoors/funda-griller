# The Note sits beside the Case and is read only by the model

The household needed to give input on one house in two ways. We split that input into two concepts. A **Correction** (_Dutch UI_ **Correctie**) replaces a Listing fact the Case computes with, and requires an explanation. It is part of the Case and feeds every deterministic figure. A **Note** (_Dutch UI_ **Notitie**) is the user's free text about the house. It is not part of the Case, because it may hold judgement ("de tuin voelt kleiner dan op de foto's") and ADR-0001 keeps the Case free of judgement. The Note is a separate input to the Verdict, which the model reads and weighs. It raises no Flag and never forces a Hard no. Changing the Note makes the Verdict Achterhaald.

## Considered Options

- **The Note in the Case as a fact.** Rejected: the Case would then carry unverifiable judgement, and Flags or a Hard no could follow from loose text.
- **Only a Note, no Correction.** Rejected: the motivating case, an agent who states the wrong living area, distorts the Expected Sale Price, the Prijsstelling, the Walk-away Maximum, the Guide Bid and the Renovation Estimate. These are all derived before the model reads anything, so a Note cannot repair them.
- **Parse the Note into Corrections with the model.** Rejected: a fact the Case computes with must be entered explicitly and traceably, not inferred.

## Consequences

- A Verdict's inputs gain the Note's version beside the Case, the Buyer Profile and the rules. "Out of date" (Achterhaald) names the Note as a cause.
- The Note goes into the Markdown export. Unlike the debts, it is not kept private.
- A Correction outranks the Listing, the register and a Finding for the same fact, which follows the existing rule that the register's energielabel outranks the Listing's. It needs no ADR of its own.
