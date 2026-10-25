# 11: Photos and Observations

**What to build:** Listing photos are downloaded and stored locally with the snapshot. The vision model reads them once and extracts Observations (kitchen and bathroom age, damp or mould, roof and facade state, renovation level), each citing its photo and marked as estimated. Observations are cached and feed Flags and the Verdict like any other fact.

**Blocked by:** 09 (Verdict and Bid Advice)

**Status:** resolved

- [x] Photos are downloaded with the snapshot and kept on disk for that snapshot
- [x] Observations are extracted by the vision model through the LLM client port and stored with the photo reference
- [x] Observations are marked estimated and show as such in the Case, per the design brief
- [x] Analysis runs once per photo set; unchanged photos are not re-analysed; re-run on demand is available
- [x] Observations can raise Flags through the rule set
- [x] A Listing with no floorplan, video or 360 photos works
- [x] Photos are shown only in the app's own UI
- [x] Tests use the fake LLM client with canned Observations

## Notes

- New port `PhotoDownloader.download(url) -> bytes` on `Ports.photo_downloader`; production adapter `app/photo_downloader.py` (https on `*.funda.nl` / `*.funda.io` only, images only, 15 MB cap). Fake: `FakePhotoDownloader`.
- `app/photos.py`: at capture each `photo_urls` entry is downloaded into `media_dir/listings/<id>/photos/` (ticket 16's store and `GET /api/listings/<id>/photos/<name>`), and the snapshot records `photos: [{number, name, url, source_url, sha256}]`. Manual uploads are used as is; a photo already on disk for the previous snapshot is reused, not downloaded again; a photo that fails to download is left out, never failing the capture.
- `app/observations.py`: runs `LlmClient.observe_photos` once per photo set (sha256 over the photos' contents in order), stores each run in `observation_runs`, and validates the answer at the boundary: keys `kitchen_age_years`, `bathroom_age_years` (int years), `damp_or_mould` (bool), `roof_condition`, `facade_condition` (good/fair/poor), `renovation_needed` (none/cosmetic/partial/full); unknown keys, wrong value kinds and photo numbers outside the set are dropped. A failed run keeps the earlier Observations.
- Case: Observation facts (`provenance: "observation"`, `estimated: true`, `photos`, `note`, `extracted_at`, `model`), plus `photos` and `observations` status (`succeeded`/`failed`/`not_run`/`no_photos`); `built_from.observation_run` makes a Verdict Achterhaald (`case`) after a re-run. Rules read them as `observation.<key>`.
- `POST /api/listings/<id>/observations` re-runs on demand (409 `no_photos`, 502/503 `llm_unavailable`).
- Flag rules v3: new condition kind `equals`; rules `damp_or_mould_visible`, `roof_poor`, `facade_poor` (risk), `kitchen_dated`, `bathroom_dated`, `full_renovation_needed` (con), with deal-breaker aliases (vocht, schimmel, dak, gevel, opknapper, renovatie).
- Gemini adapter: `observe_photos` sends photos inline, each after a `Foto n` text part, with a JSON schema; sets over 14 MB go in batches and are renumbered to the whole set.
- UI: Dossier group **Foto-waarnemingen**: thumbnail strip (app URLs only), rows with `≈` values, dashed `◔ OBS foto n · geschat` stamp whose photo numbers open the photo in a Dialog, and **Foto's opnieuw analyseren**. Signaal evidence from an Observation reads "Waarneming, geschat, foto n". Playwright: `e2e/photos.spec.ts`.
- Not done: floorplans, video and 360 photos are not part of the Listing shape, so nothing to analyse there (absent by construction); the brochure is not downloaded; Gemini Files API for very large sets (batched inline instead); the Observation prompt and value vocabulary are not yet covered by the regression set (17).
