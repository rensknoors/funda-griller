# LLM provider choice for funda-griller: Gemini vs OpenAI vs Anthropic

Researched 2026-10-24 from primary vendor docs only. Every claim has its source URL next to it. Items I could not verify are marked **UNVERIFIED** and collected at the end. Cost figures are my own arithmetic from documented prices, with the assumptions stated.

Context: one provider-swappable LLM port with three roles (vision Observations, Document Findings with page references, Verdict as structured JSON). Model IDs live in config (spec: `.scratch/funda-griller/spec.md`).

## 1. Current model IDs and tiers

### Google Gemini
Source: https://ai.google.dev/gemini-api/docs/models
- Stable: `gemini-4-argon` (flagship reasoning), `gemini-3.8-flash`, `gemini-3.6-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`.
- Preview: `gemini-3-flash-preview`, `gemini-3.1-pro-preview`. `gemini-2.5-*` is limited to existing users; `gemini-2.0-flash*` and `gemini-3-pro-preview` are shut down.
- `gemini-3.8-flash` takes text, image, video, audio and PDF input and emits text only. It has a 1,048,576 token input limit, 65,536 output, and supports structured outputs, Batch API and caching (https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash).
- `gemini-4-argon` takes the same modalities and is listed "Stable". It supports implicit caching only, not explicit (https://ai.google.dev/gemini-api/docs/models/gemini-4-argon).
- Thinking: `minimal` is not supported on 3.8 Flash and returns an error (https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash).

### OpenAI
Source: https://developers.openai.com/api/docs/models
- `gpt-6-astra` (flagship), `gpt-6.1-sol` (near-Astra at lower cost), `gpt-6-luna` (cheap, high volume). All have a 1.05M context window, 128K max output, text and image input, text output.
- The models page does not mention PDF input. The PDF guide says PDF parsing applies to "vision-capable models such as gpt-4o and later" (https://developers.openai.com/api/docs/guides/pdf-files). The `gpt-6.1-sol` model page lists text and image input and does not list file input as a modality, though structured outputs are supported (https://developers.openai.com/api/docs/models/gpt-6.1-sol).
- Cutoff for `gpt-6.1-sol` is 2026-04-30; it has a single snapshot (same model page).

### Anthropic
Source: https://platform.claude.com/docs/en/about-claude/models/overview
- `claude-fable-5-1` (top reasoning), `claude-opus-5-5`, `claude-sonnet-5-5` ("best combination of speed and intelligence"), `claude-haiku-5-5` (high-volume extraction and classification).
- All have a 1M context window and 128K max output. All current models take text and image input and are multilingual. Sonnet 5.5 retirement is "not sooner than September 28, 2027".
- Fable 5.1 is a "Covered Model" that requires 30-day data retention and is not ZDR eligible (https://platform.claude.com/docs/en/manage-claude/api-and-data-retention). Avoid it for a privacy-sensitive tool.

## 2. Image input

| | Gemini | OpenAI | Anthropic |
|---|---|---|---|
| Images per request | 3,600 | 1,500 | 600 (100 on 200k-context models) |
| Size limit | Inline bytes plus prompt must stay under 20 MB; larger goes via Files API | 512 MB total payload; 30,000 patches per image or rejected | 10 MB per image (base64); 32 MB request limit; Files API available |
| Formats | PNG, JPEG, WebP, HEIC, HEIF | PNG, JPEG, WebP, non-animated GIF | JPEG, PNG, GIF, WebP |
| Token cost | 258 tokens for images up to 384px, otherwise 768px tiles at 258 each; Gemini 3 has `media_resolution` (default 1120 tokens/image, `high` 1120, `medium` 560, `low` 280) | Patch-based: `ceil(w/32) x ceil(h/32)`, capped by a patch budget, x1.2 | `ceil(w/28) x ceil(h/28)`, up to 4,784 tokens on 4.7+ models (long edge 2,576 px) |
| Sources | https://ai.google.dev/gemini-api/docs/image-understanding , https://ai.google.dev/gemini-api/docs/media-resolution | https://developers.openai.com/api/docs/guides/images-vision | https://platform.claude.com/docs/en/build-with-claude/vision |

Practical consequences for 40 photos of ~2160x1440, ~1 MB each:
- **Gemini:** 40 MB exceeds the 20 MB inline cap, so use the Files API (files stored 48 hours, free: https://ai.google.dev/gemini-api/docs/document-processing) or chunk photos (about 15 per call).
- **Anthropic:** more than 20 images in one request triggers a stricter per-image dimension limit. The docs say resize so neither side exceeds 2,000 px or stay at 20 or fewer image/document blocks (vision page). Base64 of 40 x 1 MB is about 53 MB, over the 32 MB request limit, so use the Files API, chunk, or downscale first.
- **OpenAI:** no practical limit for this volume (512 MB, 1,500 images).
- Per the OpenAI table, 2160x1440 is 3,060 patches, over the 2,500 high-detail budget, so it is scaled down (about 3,000 tokens). The table lists `gpt-6-astra` and `gpt-5.6-*` but not `gpt-6.1-sol` or `gpt-6-luna` explicitly (**UNVERIFIED** for those two).

## 3. PDF input and page references

### Gemini
Source: https://ai.google.dev/gemini-api/docs/document-processing
- Up to 50 MB or 1,000 pages. Native vision on page images, and natively embedded text is also extracted and given to the model.
- Each page is 258 tokens in this page's wording. For Gemini 3 models, native-text tokens are not charged and page-image tokens are billed under the IMAGE modality. The pricing page says DOCUMENT tokens are billed at the image rate (https://ai.google.dev/gemini-api/docs/pricing).
- The media-resolution page gives PDF values of 560 (`medium`) and 1,120 (`high`, plus native text) but does not say "per page" (https://ai.google.dev/gemini-api/docs/media-resolution). The two pages conflict on tokens per page, so my cost estimate uses a range.
- The docs describe **no citation or page-reference feature**. Page references must be prompted.

### OpenAI
Source: https://developers.openai.com/api/docs/guides/pdf-files
- Text plus page images are extracted and both sent to the model. 50 MB per file and 50 MB combined per request. No page limit stated. `detail` (low/high) applies to the page images, and only on the Responses API.
- The page does not say whether page-level references are possible. There is no documented citation feature for PDFs.

### Anthropic
Sources: https://platform.claude.com/docs/en/build-with-claude/pdf-support , https://platform.claude.com/docs/en/build-with-claude/citations
- 32 MB request, 600 pages per request (100 if the context window is under 1M). All active models support PDFs. Each page is processed as an image plus extracted text.
- **Citations** return page ranges (`page_location`, 1-indexed) and `cited_text` does not count as output tokens. PDF citations work on extracted text only. Scanned PDFs without text are not citable, and image citations are unsupported.
- **Citations and structured outputs are incompatible.** Enabling both returns a 400 error (citations page). Findings with verifiable page references therefore need either (a) citations on, with the structured part parsed from prose or a second call, or (b) structured outputs with a `page` field filled by the model, uncited.
- Token cost per PDF page for the first-party API is not stated in the pages I fetched. The only figure is the Bedrock Converse note: about 7,000 tokens for a 3-page PDF with visual mode (about 2.3k per page) (pdf-support page). I use that as a proxy (**UNVERIFIED** for the first-party API).

### Recommendation independent of provider
No vendor guarantees page numbers. To keep the port provider-swappable, split the PDF client-side. Send each page as an image plus its extracted text with an explicit `[PAGE n]` label, and have the schema require `page`. Then verify the cited page deterministically (does the quoted text appear on that page?). I did not find a primary source that benchmarks page-number accuracy for any of the three. This design choice is mine.

## 4. Structured output / JSON schema

- **Gemini**: `response_format` with `mime_type: application/json` and a `schema` (JSON Schema subset). Pydantic `model_json_schema()` plus `model_validate_json()` is the documented Python route. `minLength`/`maxLength`, `uniqueItems` and others are ignored. Large or deeply nested schemas can return 400 INVALID_ARGUMENT. Output is syntactically valid but may be semantically wrong, so validate client-side. Model support list is not given on the page (examples use `gemini-3.8-flash`, `gemini-4-argon`). Source: https://ai.google.dev/gemini-api/docs/structured-output
- **OpenAI**: Structured Outputs guarantee schema adherence from GPT-4o onward. Python `client.responses.parse(..., text_format=PydanticModel)`. Refusals can appear in a separate `refusal` field and `status == "incomplete"` means truncated. Source: https://developers.openai.com/api/docs/guides/structured-outputs . The list of unsupported schema features is in a part of the page I could not read (**UNVERIFIED**).
- **Anthropic**: GA on Sonnet 5.5, Haiku 5.5, Opus 5.5 and others, via `output_config.format` json_schema, and `client.messages.parse(output_format=PydanticModel)`. Not supported: numerical and string constraints, recursive schemas, external `$ref`. `stop_reason: refusal` and `max_tokens` can still break the schema. Enum casing may change. First use of a schema has grammar-compile latency (cached 24 hours). Source: https://platform.claude.com/docs/en/build-with-claude/structured-outputs . The schema itself is cached up to 24 h, so keep sensitive text out of property names and enum values (same page).

All three support strict JSON for the Verdict. Anthropic's constraint enforcement is the best documented. Because tier, opening bid and walk-away max are numeric, plan to validate ranges in app code on any provider (as the spec already says).

## 5. Dutch capability

- Gemini: Google's model docs state that all Gemini models can understand Dutch (nl) and text-capable models can respond in it. I found this only via a search snippet of the Google Cloud models page, and the `ai.google.dev` model pages say nothing about languages (https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash , https://ai.google.dev/gemini-api/docs/models/gemini-4-argon). Treat as weakly verified. Cloud docs: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/google-models
- Anthropic: "robust multilingual capabilities" and "most world languages" but Dutch is not in the benchmark table, which covers older models (Sonnet 4.5, Haiku 4.5): https://platform.claude.com/docs/en/build-with-claude/multilingual-support . No Dutch-specific claim.
- OpenAI: no Dutch statement found on the pages I read (**UNVERIFIED**).
- No primary-source Dutch benchmark exists for any of them. Dutch quality for housing/legal vocabulary (Vragenlijst, erfpacht, VvE) has to be tested with the spec's regression set.

## 6. Pricing (USD per 1M tokens, standard, as of 2026-10-24)

| Model | Input | Output | Cache read | Batch (in/out) | Source |
|---|---|---|---|---|---|
| `gemini-3.8-flash` | 0.75 until 2026-12-31, then 1.50 | 3.75, then 7.50 | 0.075, then 0.15 (+ storage $0.50/MTok/h) | half | https://ai.google.dev/gemini-api/docs/pricing |
| `gemini-4-argon` | 2.00 until 2026-11-30, then 4.00 | 10, then 20 | 0.10, then 0.20 (implicit only) | half | same |
| `gemini-3.5-flash-lite` | 0.30 | 2.50 | 0.03 | 0.15 / 1.25 | same |
| `claude-sonnet-5-5` | 2 | 10 | 0.10 (0.05x) | 1 / 5 | https://platform.claude.com/docs/en/about-claude/pricing |
| `claude-haiku-5-5` | 0.10 (prompts up to 100k), 0.50 above | 0.50 / 2.50 | 0.01 / 0.05 | 0.05 / 0.25 (up to 100k) | same |
| `claude-opus-5-5` | 4 | 20 | 0.20 | 2 / 10 | same |
| `gpt-6.1-sol` | 2 (4 above 272k) | 10 (15) | 0.10 | 1 / 5 | https://developers.openai.com/api/docs/pricing |
| `gpt-6-luna` | 0.10 | 0.50 | 0.01 | 0.05 / 0.25 | same |
| `gpt-6-astra` | 10 | 50 | 1.00 | 5 / 25 | same |

Notes:
- Gemini Flash prices are **promotional and double on 2027-01-01** (Argon doubles on 2026-12-01). The budget should use the post-promo price.
- Anthropic: 5-minute cache write is 1.25x and a US-only inference option is 1.1x (pricing page). Anthropic's 1M context is at standard price (Haiku 5.5 is tiered at 100k).
- OpenAI: batch/flex is 50%, and cached input is 0.05x on Sol (https://developers.openai.com/api/docs/guides/prompt-caching). Batch API has a 24 h window, up to 50,000 requests and 200 MB input (https://developers.openai.com/api/docs/guides/batch).
- Gemini Batch is 50% with 24 h target; caching works with batch (https://ai.google.dev/gemini-api/docs/batch-api).
- Caching is irrelevant to this workload except for the Verdict re-runs (same Case, changed profile). Batch is also mostly irrelevant for an interactive tool, though it could suit the regression set.

### Estimated cost per house (my arithmetic)
Assumptions: 40 photos (2160x1440), a 32-page PDF, one Verdict. Verdict input about 8k tokens. Output (Observations, Findings, Verdict, including thinking) about 20k tokens total. These are guesses and thinking tokens could move them a lot.

| Model | Image tokens (40) | PDF tokens (32 pages) | Total input | Approx. cost now | Approx. steady state |
|---|---|---|---|---|---|
| `gemini-3.8-flash` | 40 x 1,120 = 45k | 8k (258/page) to 36k (1,120/page) | 61k to 89k | about $0.11 to $0.14 | about $0.22 to $0.28 (post-2027 pricing) |
| `gemini-4-argon` | same | same | same | about $0.32 to $0.38 | about $0.64 to $0.76 (post-promo) |
| `gemini-3.5-flash-lite` | same | same | same | about $0.07 to $0.08 | same |
| `claude-sonnet-5-5` | 3,456 each if resized to 2000 px, so 138k (full size 4,056 each, 162k) | about 75k (proxy) | about 220k | about $0.65 | same |
| `claude-haiku-5-5` | same 138k | about 75k | about 220k per call (over 100k, so higher tier unless split) | about $0.20 in one call, about $0.06 if split under 100k | same |
| `gpt-6.1-sol` | about 3,000 each = 120k | ~50k to 100k (not documented) | ~180k to 230k | about $0.60 to $0.70 | same |
| `gpt-6-luna` | same | same | same | about $0.03 to $0.04 | same |

At low volume (a few dozen houses a year), every option costs from cents to a few dollars a year. **Cost is not the deciding factor.** Image token counts per model are from the formulas above and are estimates.

## 7. Paid-tier data use, retention, residency

### Google (Gemini API)
Source: https://ai.google.dev/gemini-api/terms
- Paid Services: prompts and responses are **not used to improve Google's products**. Processed under the Data Processing Addendum for Products Where Google is a Data Processor.
- Logged "for a limited period of time" solely for abuse detection, safety and legal disclosure. **Period not stated.** The page does not address human review for paid services.
- Data "may be stored transiently or cached in any country where Google or its agents have facilities". No EU residency commitment on the Developer API terms.
- Unpaid Services: content is used to improve products and human reviewers may read it, and sensitive data should not be submitted. In EEA, Switzerland and UK the paid-service terms apply to all services (same page).
- Files API uploads are kept for 48 hours (https://ai.google.dev/gemini-api/docs/document-processing).
- EU residency exists on **Vertex AI** (Google Cloud) via the `eu` multi-region endpoint, which keeps ML processing in EU member states. Global endpoints give no guarantee. Both `gemini-3.8-flash` and `gemini-4-argon` appear in the Vertex models table, but I could not read which regions they support (https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/data-residency). The Developer API data-residency page 404s (https://ai.google.dev/gemini-api/docs/data-residency).

### OpenAI
Source: https://developers.openai.com/api/docs/guides/your-data
- API data is not used for training by default (opt-in only).
- Abuse-monitoring logs are kept up to 30 days. Zero Data Retention and Modified Abuse Monitoring need prior approval.
- EU data residency via `eu.api.openai.com` (EEA + Switzerland) exists, but "requires ZDR, Modified Abuse Monitoring, Private Retention with PSP, or Safety Retention", i.e. approved arrangements. This is probably not obtainable for a personal account (inference). Some models carry a 10% uplift (https://developers.openai.com/api/docs/pricing).
- Image and file inputs flagged by the CSAM classifier are retained for manual review even under ZDR (your-data page).

### Anthropic
Sources: https://platform.claude.com/docs/en/manage-claude/api-and-data-retention , https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data , https://platform.claude.com/docs/en/manage-claude/data-residency
- Retained data is never used for training without express permission (retention page). Uploaded images are ephemeral and not used to train models (vision page FAQ).
- Standard API retention: inputs and outputs are deleted from the backend within 30 days (privacy.claude.com page). The developer docs separately say conversation content is "not retained by default" (retention page). **These two statements do not match as fetched**, so treat 30 days as the safe assumption.
- Flagged content may be kept up to 2 years (retention page) and classification scores up to 7 years (privacy page).
- **Residency: only `us` or `global` inference, and only a `us` workspace geo.** There is no EU option on the first-party API (data-residency page). EU regional endpoints exist on Amazon Bedrock and Google Cloud (Google managed) (overview page, "regional endpoints", with a 10% premium on those partner platforms per pricing page). Bedrock only accepts base64 images (vision page).

Net: nobody offers an easy EU-resident path for a personal single-household account. EU-only processing would mean Vertex `eu` (Gemini) or Bedrock/Vertex regional (Claude), which adds cloud-account complexity. All three say paid API data is not trained on. The spec already accepts "photos and PDFs sent in full".

## 8. Comparison

| Criterion | Gemini 3.8 Flash | Claude Sonnet 5.5 (or Haiku 5.5) | OpenAI gpt-6.1-sol (or Luna) |
|---|---|---|---|
| Native PDF | Yes, 50 MB / 1,000 pages | Yes, 32 MB / 600 pages | Yes, 50 MB, page limit undocumented; model page does not list file input |
| Photo count/size friction | 20 MB inline cap, use Files API | 32 MB request and 2,000 px rule above 20 images | Lowest friction |
| Page references | Prompt-only | Citations give page ranges, but not with structured outputs and not for scans | Prompt-only |
| Structured JSON | Yes (subset, validate) | Yes (GA, best documented limits) | Yes (strict) |
| Cost per house (est.) | ~$0.11-0.14 now, ~$0.22-0.28 post-promo | ~$0.65 (Sonnet), cheaper with Haiku | ~$0.60-0.70 (Sol), ~$0.04 (Luna) |
| Training on paid data | No | No | No (default) |
| Retention | "Limited period", unstated | 30 days (privacy page) | Up to 30 days |
| EU residency | Vertex `eu` only; not on Developer API | Not on first-party API (US/global); Bedrock/Vertex regional | `eu.api.openai.com` but needs approved retention program |
| Dutch documented | Weak (cloud docs, via search) | Generic multilingual only | Not found |
| Batch / caching | 50% batch, implicit cache | 50% batch, cache reads 0.05-0.1x | 50% batch, cache reads 0.05-0.1x |

## 9. Recommendation per role

No primary source here benchmarks quality on Dutch real-estate photos, so quality-based choices below are judgement and must be settled by the spec's 5-10 house regression set. Weighing documented facts only:

1. **Vision (Observations): Gemini 3.8 Flash**, the user's current choice. It has the highest image-count cap, the lowest cost per photo and native multi-image input. Use the Files API or chunk to stay under 20 MB, and set `media_resolution` explicitly (`high` for photos). Fallback: `claude-haiku-5-5` (cheap) if you need a second opinion, or `gpt-6-luna`.
2. **Document Findings: start with Gemini 3.8 Flash using client-side page splitting and explicit `[PAGE n]` labels, then verify quoted text against the page.** If page-number accuracy or Dutch legal reading disappoints in the regression set, swap this one role to `claude-sonnet-5-5`, with citations enabled for page-range grounding (parse the Findings from the cited output, since citations can't be combined with structured outputs). Native text-layer PDFs only for the citations route.
3. **Verdict: either.** Input is small text and no raw financial data is sent, so privacy is not provider-differentiating. Keeping it on Gemini 3.8 Flash avoids a second key and SDK. A different family (Sonnet 5.5 or `gemini-4-argon`) is worth trying if tiers feel miscalibrated; the extra cost per Verdict is a few cents.

**Overall:** Gemini 3.8 Flash for all three roles is the simplest and cheapest, and consistent with ADR direction. Keep the port generic so one role can move to Anthropic. Do not pick OpenAI unless a test shows it wins on quality: it offers the least documented PDF handling, no documented page references, and EU residency that needs an approved retention program. Budget for the Gemini price doubling on 2027-01-01. Re-check the Gemini paid terms (retention period undefined) at setup, as the spec already notes.

## 10. Unverified / gaps

- Quality: no vendor benchmark for Dutch real-estate photos, Dutch legal PDFs, or page-reference accuracy. Do not treat the recommendation as quality-proven.
- Dutch support: OpenAI statement not found; Gemini only via a search snippet of the Google Cloud models page; Anthropic has no Dutch-specific data and its table covers older models.
- Gemini tokens per PDF page: two pages conflict (258 vs 560/1,120). Anthropic first-party tokens per PDF page not stated (I used the Bedrock figure of about 2.3k/page). OpenAI PDF token cost not stated; Sol/Luna image patch rules not listed explicitly.
- OpenAI: whether `gpt-6.1-sol`/`gpt-6-luna` accept PDF `input_file` (guide says "vision-capable models", model pages don't list files); the structured-output unsupported-feature list was beyond the readable portion; Data residency guide URL `/guides/data-residency` returned 404, so which models are eligible for `eu.api.openai.com` is unconfirmed.
- Google: Developer API EU residency page (404); exact abuse-log retention period; which Vertex regions serve `gemini-3.8-flash`/`gemini-4-argon`; Gemini rate limits at the paid tier.
- Anthropic: discrepancy between "not retained by default" (docs) and "deleted within 30 days" (privacy article); Bedrock/Vertex EU endpoint availability for Sonnet 5.5 specifically; whether 40 photos plus a PDF fit the 32 MB request size without the Files API (they do not at full size, per my estimate).
- All cost numbers are estimates with assumed output length and ignore thinking-token variance.
