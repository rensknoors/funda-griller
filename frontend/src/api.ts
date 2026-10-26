export type Snapshot = {
  id: number;
  fetched_at: string;
  raw_status: string;
  status: string;
  address: string | null;
  city: string | null;
  asking_price: number | null;
  living_area: number | null;
  plot_area: number | null;
  energy_label: string | null;
  photo_urls: string[];
  /** How the snapshot came in; absent on snapshots stored before manual entry existed. */
  entry?: "fetched" | "manual";
  price_history: { date: string | null; price: number | null }[];
};

/** Verdict tiers in their sort order. `null` until a Verdict exists (a Hard no comes from the Case). */
export type Tier = "must_buy" | "consider" | "skip" | "hard_no";

/** One Listing's row in the comparison view, read off its snapshots and Case. */
export type Comparison = {
  tier: Tier | null;
  hard_no_reason: string | null;
  status: string;
  status_change: { from: string; to: string } | null;
  asking_price: number | null;
  previous_asking_price: number | null;
  living_area: number | null;
  plot_area: number | null;
  energy_label: { value: string; official: boolean } | null;
  asking_vs_woz_percent: number | null;
  asking_vs_comparables_percent: number | null;
  headroom: number | null;
  flag_counts: { pro: number; con: number; risk: number };
  stale_count: number;
  last_fetched_at: string;
};

export type Listing = {
  funda_id: string;
  url: string;
  archived: boolean;
  snapshots: Snapshot[];
  comparison: Comparison;
};

/** How long a request may take before the UI gives up and shows an error, per kind of work. */
export const TIMEOUT_MS = {
  /** Reads and quick checks. */
  quick: 10_000,
  /** A Listing or Source fetch: provider, Sources, photo download and Observations. */
  capture: 180_000,
  /** A model call over the Case, photos or a Document. */
  model: 300_000,
} as const;

/**
 * `fetch` that rejects after `timeoutMs`, so a backend that accepts the connection but never
 * answers ends in the caller's error state instead of an endless spinner or disabled button.
 */
export function apiFetch(path: string, init: RequestInit = {}, timeoutMs: number = TIMEOUT_MS.quick) {
  const timeout = AbortSignal.timeout(timeoutMs);
  const signal = init.signal ? AbortSignal.any([init.signal, timeout]) : timeout;
  return fetch(path, { ...init, signal });
}

export type CaptureError =
  | { kind: "bad_url" }
  | { kind: "listing_removed" }
  | { kind: "provider_blocked" }
  | { kind: "already_captured"; fundaId: string }
  | { kind: "no_response" }
  | { kind: "unknown" };

/** All Listings, archived ones included: the view hides those unless asked. */
export async function fetchListings(): Promise<Listing[]> {
  const response = await apiFetch("/api/listings?include_archived=true");
  if (!response.ok) throw new Error("listings unavailable");
  return response.json();
}

async function setArchived(fundaId: string, action: "archive" | "restore"): Promise<Listing> {
  const response = await apiFetch(`/api/listings/${fundaId}/${action}`, { method: "POST" });
  if (!response.ok) throw new Error(`${action} unavailable`);
  return response.json();
}

export const archiveListing = (fundaId: string) => setArchived(fundaId, "archive");
export const restoreListing = (fundaId: string) => setArchived(fundaId, "restore");

async function post(path: string, body?: unknown): Promise<Listing | CaptureError> {
  let response: Response;
  try {
    response = await apiFetch(
      path,
      {
        method: "POST",
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      },
      TIMEOUT_MS.capture,
    );
  } catch {
    return { kind: "no_response" };
  }
  try {
    const payload = await response.json();
    if (response.ok) return payload as Listing;
    if (payload.code === "already_captured") {
      return { kind: "already_captured", fundaId: payload.funda_id };
    }
    if (["bad_url", "listing_removed", "provider_blocked"].includes(payload.code)) {
      return { kind: payload.code } as CaptureError;
    }
  } catch {
    // fall through to unknown
  }
  return { kind: "unknown" };
}

export const captureListing = (url: string) => post("/api/listings", { url });
export const refetchListing = (fundaId: string) => post(`/api/listings/${fundaId}/refetch`);

export type ManualEntryError =
  | { kind: "bad_url" }
  | { kind: "already_captured"; fundaId: string }
  | { kind: "not_an_image" }
  | { kind: "invalid"; errors: Record<string, string> }
  | { kind: "unknown" };

/** Fallback when fetching is blocked: the form's fields and photos as multipart form data. */
export async function enterListing(form: FormData): Promise<Listing | ManualEntryError> {
  try {
    const response = await apiFetch("/api/listings/manual", { method: "POST", body: form }, TIMEOUT_MS.capture);
    const payload = await response.json();
    if (response.ok) return payload as Listing;
    if (payload.code === "already_captured") return { kind: "already_captured", fundaId: payload.funda_id };
    if (payload.code === "bad_url" || payload.code === "not_an_image") return { kind: payload.code };
    if (Array.isArray(payload.errors)) {
      const errors: Record<string, string> = {};
      for (const { field, message } of payload.errors as { field: string; message: string }[]) {
        errors[field] = message;
      }
      return { kind: "invalid", errors };
    }
  } catch {
    // fall through to unknown
  }
  return { kind: "unknown" };
}

export function isCaptureError(result: Listing | CaptureError): result is CaptureError {
  return "kind" in result;
}

export type ListingFact = {
  key: string;
  value: string | number;
  provenance: "listing";
  fetched_at: string;
};

export type SourceTrust = "official" | "third_party";

/** A nearby Listing from the comparables Source; prices are its (last) asking price. */
export type Comparable = {
  funda_id: string;
  address: string | null;
  city: string | null;
  asking_price: number | null;
  living_area: number | null;
  raw_status: string | null;
  recently_sold: boolean;
  url: string | null;
};

export type CommuteMode = "car" | "bike";

/** Travel time to one Koperprofiel commute destination: the faster of car and bike counts; public
 * transport is not included. */
export type CommuteTravel = {
  destination: string;
  minutes: number;
  mode: CommuteMode;
  minutes_by_mode: Partial<Record<CommuteMode, number>>;
  public_transport: false;
};

/** A commute destination the Source could not place or route: shown as unknown, never judged. */
export type CommuteUnknown = {
  destination: string;
  minutes: null;
  unavailable: "destination_not_found" | "no_route";
};

export type CommuteFact = CommuteTravel | CommuteUnknown;

export type SourceFact = {
  key: string;
  value: string | number | Comparable | CommuteFact;
  as_of: string | null;
  provenance: "source";
  source: string;
  trust: SourceTrust;
  fetched_at: string;
  ttl_days: number | null;
  stale: boolean;
};

/** What a Finding is about; mirrors the backend's topic list. */
export type FindingTopic =
  | "asbestos"
  | "leak"
  | "solar_lease"
  | "erfpacht"
  | "subsidy"
  | "stays_or_goes"
  | "foundation"
  | "other";

/** A seller-stated fact from a Document, with the page it is on. */
export type FindingFact = {
  key: FindingTopic;
  /** Whether the seller states it applies. */
  value: boolean;
  statement: string;
  /** The words on the page the Finding rests on, as the model quoted them. */
  quote: string | null;
  page: number;
  /** The quote was found on the cited page; false when the page has no text to check (a scan). */
  verified: boolean;
  provenance: "finding";
  seller_stated: true;
  document_id: number;
  document_name: string;
  extracted_at: string;
};

export type DocumentStatus = "pending" | "analysed" | "unreadable" | "not_analysed" | "download_failed";

/** A Document as the Case lists it. */
export type CaseDocument = {
  id: number;
  name: string;
  kind: "user" | "brochure";
  status: DocumentStatus;
  reason: string | null;
  page_count: number | null;
  finding_count: number;
  rejected_findings: number;
  added_at: string;
  extracted_at: string | null;
};
/** A Listing photo kept by the app, numbered from 1; `url` is always the app's own. */
export type CasePhoto = { number: number; url: string };

/** Observation (Waarneming): estimated by the vision model from the cited photos. */
export type ObservationFact = {
  key: string;
  value: string | number | boolean;
  note: string | null;
  photos: CasePhoto[];
  provenance: "observation";
  estimated: true;
  extracted_at: string;
  model: string | null;
};

export type ObservationStatus = {
  status: "succeeded" | "failed" | "not_run" | "no_photos";
  reason: string | null;
  attempted_at: string | null;
  model: string | null;
};

export type CaseFact = ListingFact | SourceFact | ObservationFact | FindingFact;

export type SourceStatus = {
  source: string;
  status: "succeeded" | "failed" | "skipped";
  reason: string | null;
  attempted_at: string | null;
  trust: SourceTrust;
};

export type Metrics = {
  energy_label_check: {
    listing: string;
    register: string;
    matches: boolean;
    provenance: "computed";
  } | null;
  asking_vs_woz: {
    asking_price: number;
    woz_value: number;
    woz_as_of: string;
    difference: number;
    percent: number;
    provenance: "computed";
  } | null;
  asking_vs_comparables: AskingVsComparables;
  /** Koperprofiel commute destinations with no travel time for their current address (added, or
   * address changed since the last fetch): not judged until the commute Source is fetched again. */
  commute_coverage: { not_fetched: string[]; provenance: "computed" } | null;
};

/** Coverage says plainly whether comparables were fetched and whether there are enough to lean on. */
export type ComparablesCoverage = "not_fetched" | "none" | "thin" | "sufficient";

export type AskingVsComparables = {
  coverage: ComparablesCoverage;
  count: number;
  min_count: number;
  price_per_m2: number | null;
  median_price_per_m2: number | null;
  percent: number | null;
  comparables_value: number | null;
  provenance: "computed";
};

export type Affordability = {
  max_mortgage: number;
  energy_label_bonus: number;
  equity: number;
  kosten_koper: { transfer_tax: number; fixed_costs: number; total: number } | null;
  mortgage_needed: number | null;
  monthly_cost: number | null;
  headroom: number | null;
  /** Highest purchase price the household can pay, kosten koper included. */
  affordable_maximum: number;
  /** The energielabel the borrowing capacity was computed with (register over Listing). */
  energy_label: string | null;
  provenance: "computed";
  computed_on: string;
};

export type Evidence = {
  key: string;
  value: string | number | boolean | string[] | null;
  provenance: string;
  fetched_at?: string | null;
  /** Findings only: the Document and page the evidence is on. */
  page?: number;
  document_id?: number;
  document_name?: string;
  statement?: string;
  /** Observations only: estimated, with the photos they were read from. */
  estimated?: boolean;
  photos?: CasePhoto[];
  /** Commute travel time only: the destination and the modes behind `value`. */
  commute?: CommuteTravel;
};

export type FlagClass = "pro" | "con" | "risk";

export type Flag = {
  id: string;
  rule_id: string;
  rule_version: number;
  class: FlagClass;
  title: string;
  evidence: Evidence[];
};

export type HardNo = { tier: "hard_no"; deal_breaker: string; flag_id: string };

export type Case = {
  funda_id: string;
  built_from: {
    snapshot_id: number;
    profile_version: number | null;
    flag_rules_version: number;
    observation_run: number | null;
    documents: { id: number; sha256: string | null; status: DocumentStatus }[];
  };
  facts: CaseFact[];
  sources: SourceStatus[];
  photos: CasePhoto[];
  observations: ObservationStatus;
  documents: CaseDocument[];
  metrics: Metrics;
  affordability: Affordability | null;
  flags: Flag[];
  hard_no: HardNo | null;
  rules: { year: number; is_current_year: boolean };
};

export async function fetchCase(fundaId: string): Promise<Case> {
  const response = await apiFetch(`/api/listings/${fundaId}/case`);
  if (!response.ok) throw new Error("case unavailable");
  return response.json();
}

/** Manually refetch one Source; returns the rebuilt Case. Nothing refetches by itself. */
export async function refetchSource(fundaId: string, source: string): Promise<Case> {
  // Comparables fetch several Listings in one go, so this gets the capture budget.
  const response = await apiFetch(
    `/api/listings/${fundaId}/sources/${source}/refetch`,
    { method: "POST" },
    TIMEOUT_MS.capture,
  );
  if (!response.ok) throw new Error("source refetch unavailable");
  return response.json();
}

const documentsPath = (fundaId: string) => `/api/listings/${fundaId}/documents`;

async function sendDocument(path: string, method: "POST" | "PUT", file: File): Promise<void> {
  const form = new FormData();
  form.append("file", file);
  const response = await apiFetch(path, { method, body: form }, TIMEOUT_MS.model);
  if (!response.ok) throw new Error("document upload failed");
}

/** Upload a Document; its Findings are extracted before this resolves. */
export const uploadDocument = (fundaId: string, file: File) =>
  sendDocument(documentsPath(fundaId), "POST", file);

/** Re-upload: the file replaces the Document and its Findings. */
export const replaceDocument = (fundaId: string, documentId: number, file: File) =>
  sendDocument(`${documentsPath(fundaId)}/${documentId}`, "PUT", file);

export async function removeDocument(fundaId: string, documentId: number): Promise<void> {
  const response = await apiFetch(`${documentsPath(fundaId)}/${documentId}`, { method: "DELETE" });
  if (!response.ok) throw new Error("document removal failed");
}

/** Retry a Document that was not analysed, or a brochure whose download failed. */
export async function analyseDocument(fundaId: string, documentId: number): Promise<void> {
  const response = await apiFetch(`${documentsPath(fundaId)}/${documentId}/analyse`, { method: "POST" }, TIMEOUT_MS.model);
  if (!response.ok) throw new Error("document analysis failed");
}

/** The Document itself, served only to this app; `page` opens it at that page. */
export const documentFileUrl = (fundaId: string, documentId: number, page?: number) =>
  `${documentsPath(fundaId)}/${documentId}/file${page ? `#page=${page}` : ""}`;

/** Re-run the vision model over the latest snapshot's photos; returns the rebuilt Case. */
export async function rerunObservations(fundaId: string): Promise<Case> {
  const response = await apiFetch(`/api/listings/${fundaId}/observations`, { method: "POST" }, TIMEOUT_MS.model);
  if (!response.ok) throw new Error("observations unavailable");
  return response.json();
}

/** What changed since a Verdict was made; any entry makes it out of date (Achterhaald). */
export type VerdictInput = "case" | "buyer_profile" | "rules" | "model";

/**
 * The Walk-away Maximum is the lower of the betaalruimte and its basis plus a margin. The basis is
 * the comparables value when they are sufficient, else the asking price; with neither, the
 * betaalruimte alone. Anything but comparables is weakly grounded.
 */
export type WalkAwayDerivation = {
  basis: "comparables" | "asking_price" | "affordability";
  margin: number | null;
  basis_maximum: number | null;
  binding: "basis" | "affordability";
  weakly_grounded: boolean;
};

export type BidAdvice = {
  opening_bid: number;
  walk_away_maximum: number;
  conditions: string[];
  affordable_maximum: number;
  /** Absent on Verdicts made before comparables existed. */
  comparables?: {
    coverage: ComparablesCoverage;
    count: number;
    comparables_value: number | null;
    maximum: number | null;
  };
  /** How the Walk-away Maximum was derived; absent on Verdicts whose model proposed it. */
  derivation?: WalkAwayDerivation;
  asking_price: number | null;
  monthly_cost_at_asking_price: number | null;
  monthly_cost_at_walk_away_maximum: number | null;
};

export type Verdict = {
  id: number;
  version: number;
  created_at: string;
  tier: Tier;
  summary: string;
  reasoning: string;
  deal_breaker: string | null;
  cited_flags: { id: string; title: string; class: FlagClass }[];
  bid_advice: BidAdvice | null;
  deterministic: boolean;
  built_from: {
    snapshot_id: number;
    profile_version: number | null;
    flag_rules_version: number;
    rules_year: number;
    source_fetches: Record<string, string>;
    model: string | null;
  };
};

export type VerdictState = {
  /** Newest first. */
  verdicts: Verdict[];
  out_of_date: boolean;
  changed: VerdictInput[];
};

export type VerdictError =
  | { kind: "no_buyer_profile" }
  | { kind: "invalid_verdict"; problems: string[] }
  | { kind: "llm_unavailable" }
  | { kind: "unknown" };

export async function fetchVerdicts(fundaId: string): Promise<VerdictState> {
  const response = await apiFetch(`/api/listings/${fundaId}/verdict`);
  if (!response.ok) throw new Error("verdict unavailable");
  return response.json();
}

/** Ask for a new Verdict version. Never happens by itself. */
export async function runVerdict(fundaId: string): Promise<Verdict | VerdictError> {
  try {
    const response = await apiFetch(`/api/listings/${fundaId}/verdict`, { method: "POST" }, TIMEOUT_MS.model);
    const payload = await response.json();
    if (response.ok) return payload as Verdict;
    if (payload.code === "invalid_verdict") return { kind: "invalid_verdict", problems: payload.problems };
    if (payload.code === "no_buyer_profile" || payload.code === "llm_unavailable") return { kind: payload.code };
  } catch {
    // fall through to unknown
  }
  return { kind: "unknown" };
}

export function isVerdictError(result: Verdict | VerdictError): result is VerdictError {
  return "kind" in result;
}

export type OutOfDateVerdicts = {
  count: number;
  verdicts: { funda_id: string; verdict_id: number; tier: Tier; changed: VerdictInput[] }[];
};

/** Listings whose newest Verdict is Achterhaald, e.g. for "Dit verandert N oordelen" after a profile save. */
export async function fetchOutOfDateVerdicts(): Promise<OutOfDateVerdicts> {
  const response = await apiFetch("/api/verdicts/out-of-date");
  if (!response.ok) throw new Error("out-of-date verdicts unavailable");
  return response.json();
}
