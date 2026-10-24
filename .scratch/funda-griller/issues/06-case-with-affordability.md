# 06: Case with affordability

**What to build:** A Case detail screen for a Listing, assembled deterministically from the latest Listing snapshot and the current Buyer Profile. It shows Listing facts with provenance, and the computed affordability: maximum mortgage, kosten koper, equity from the current home, monthly cost at the asking price, and headroom above the ask. The rule year behind the numbers is displayed. The Case contains no judgement.

**Blocked by:** 04 (Capture a Listing by URL), 05 (Buyer Profile)

**Status:** ready-for-agent

- [ ] Opening a Listing shows its Case: Listing facts, each labelled with provenance
- [ ] Maximum mortgage, kosten koper, equity, monthly cost at asking price and bidding headroom are computed from the profile and the Listing
- [ ] Affordability is driven by a data table per year; the year used is shown on the Case
- [ ] The energielabel's effect on borrowing capacity is included
- [ ] The Case is rebuilt when the profile or snapshot changes and records which versions produced it
- [ ] The Case builder does no I/O and no judgement
- [ ] API tests with fixture profiles cover typical, low-income and high-equity households
- [ ] The Case detail screen is built to the design brief
