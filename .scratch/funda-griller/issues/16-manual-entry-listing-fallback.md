# 16: Manual-entry Listing fallback

**What to build:** A second Listing provider adapter, a manual-entry form with photo upload, that produces the same Listing shape as the pyfunda adapter, so a Case can still be built when the fetch provider is broken or blocked.

**Blocked by:** 04 (Capture a Listing by URL)

**Status:** resolved

- [x] A form captures the core Listing facts and accepts uploaded photos
- [x] The result is stored as a normal Listing snapshot and flows through Case and Verdict unchanged
- [x] The fetch error screen offers manual entry when the provider is blocked
- [x] Both adapters satisfy the same provider port contract tests

## Notes

- `app/manual_provider.py`: `ManualListingProvider(entry).fetch(url) -> Listing`, the second adapter on the Listing provider port. `tests/test_listing_provider_contract.py` runs the same contract (id from URL, core facts, serialisable, bad URL rejected) against both adapters.
- `POST /api/listings/manual` (multipart: `url`, `raw_status`, core facts, `photos[]`) goes through the same capture path as a fetch, so the snapshot is a normal Listing snapshot; it records `entry: "manual"` (fetched snapshots record `"fetched"`; older ones have no `entry`). Blank fields mean unknown. Non-image uploads are rejected (422 `not_an_image`); a captured URL is a duplicate (409), like Ophalen.
- Photos are stored under `media_dir/listings/<id>/photos/` with generated names and served at `GET /api/listings/<id>/photos/<name>`; `photo_urls` hold those app URLs, ready for Observations (11).
- Case: covered by API test (facts with Listing provenance, affordability). Verdict does not exist yet; it reads the Case, so it is covered by construction (09).
- UI: the "aanbieder geblokkeerd" error offers **Handmatig invoeren**, which opens a vakken form prefilled with the URL; manual snapshots carry a "Handmatig ingevoerd" chip in the list and Dossier header. Playwright: `e2e/manual-entry.spec.ts`.
- Not done: manual entry as a fallback for a blocked *refetch* of an existing Listing (409 today); price history, coordinates and brochure are not part of the form; showing photos in the UI belongs to 11.
- New dependency: `python-multipart` (FastAPI form/file parsing).
