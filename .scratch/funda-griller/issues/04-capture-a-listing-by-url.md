# 04: Capture a Listing by URL

**What to build:** The user pastes a funda URL and the Listing is fetched through the Listing provider port (pyfunda adapter), stored as an immutable timestamped snapshot, and shown in the Listings list. The snapshot keeps the raw status string, price history and photo URLs. Pasting a URL already captured offers a re-fetch instead of creating a duplicate. Failures are told apart: bad URL, removed listing, provider blocked.

**Blocked by:** 01 (Scaffold and test harness), 03 (Design direction)

**Status:** resolved

- [x] Pasting a funda URL creates a Listing snapshot with price, areas, rooms, build year, energielabel, coordinates, heating and description, where present
- [x] The raw status string, asking-price history and photo and brochure URLs are stored on the snapshot
- [x] The Listing is keyed on the funda id from the URL; the provider's internal id is stored separately
- [x] Missing floorplan, video and 360 data does not cause an error
- [x] Pasting an existing URL offers a re-fetch that creates a new snapshot and keeps the old one
- [x] Bad URL, removed listing and provider-blocked produce distinct errors in the API and UI
- [x] The provider never calls the library's search function
- [x] Provider output is parsed defensively; attribute shape differences between a sold and a live listing both work
- [x] The snapshot serialiser stores the provider's objects correctly (not as empty output)
- [x] API tests run against fixtures recorded from the two prototype listings; no network in tests
- [x] The Listings list screen shows captured Listings, built to the design brief
