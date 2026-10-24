# 16: Manual-entry Listing fallback

**What to build:** A second Listing provider adapter, a manual-entry form with photo upload, that produces the same Listing shape as the pyfunda adapter, so a Case can still be built when the fetch provider is broken or blocked.

**Blocked by:** 04 (Capture a Listing by URL)

**Status:** ready-for-agent

- [ ] A form captures the core Listing facts and accepts uploaded photos
- [ ] The result is stored as a normal Listing snapshot and flows through Case and Verdict unchanged
- [ ] The fetch error screen offers manual entry when the provider is blocked
- [ ] Both adapters satisfy the same provider port contract tests
