# 05: Buyer Profile

**What to build:** The user enters and edits their Buyer Profile in a form: household composition, income, assets, current home value, outstanding mortgage and selling costs, plus must-haves, nice-to-haves, deal-breakers, commute destinations and renovation tolerance. It is validated, stored locally and versioned. The backend can produce the reduced profile (derived figures and preferences only) that is later allowed to reach the LLM.

**Blocked by:** 01 (Scaffold and test harness), 03 (Design direction)

**Status:** ready-for-agent

- [ ] The profile form covers every field above and is built to the design brief
- [ ] Obviously invalid input (negative income, impossible dates, empty required fields) is rejected with clear messages
- [ ] Saving creates a new profile version; earlier versions are retained
- [ ] Data is stored only locally and is never included in any outbound call by this ticket
- [ ] The reduced profile can be produced from the stored profile and contains no raw income, asset balances or address
- [ ] API tests cover create, edit, versioning, validation and the reduced-profile shape
