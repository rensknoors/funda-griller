# 11: Photos and Observations

**What to build:** Listing photos are downloaded and stored locally with the snapshot. The vision model reads them once and extracts Observations (kitchen and bathroom age, damp or mould, roof and facade state, renovation level), each citing its photo and marked as estimated. Observations are cached and feed Flags and the Verdict like any other fact.

**Blocked by:** 09 (Verdict and Bid Advice)

**Status:** ready-for-agent

- [ ] Photos are downloaded with the snapshot and kept on disk for that snapshot
- [ ] Observations are extracted by the vision model through the LLM client port and stored with the photo reference
- [ ] Observations are marked estimated and show as such in the Case, per the design brief
- [ ] Analysis runs once per photo set; unchanged photos are not re-analysed; re-run on demand is available
- [ ] Observations can raise Flags through the rule set
- [ ] A Listing with no floorplan, video or 360 photos works
- [ ] Photos are shown only in the app's own UI
- [ ] Tests use the fake LLM client with canned Observations
