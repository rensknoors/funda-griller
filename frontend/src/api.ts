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

export type CaptureError =
  | { kind: "bad_url" }
  | { kind: "listing_removed" }
  | { kind: "provider_blocked" }
  | { kind: "already_captured"; fundaId: string }
  | { kind: "unknown" };

/** All Listings, archived ones included: the view hides those unless asked. */
export async function fetchListings(): Promise<Listing[]> {
  const response = await fetch("/api/listings?include_archived=true");
  if (!response.ok) throw new Error("listings unavailable");
  return response.json();
}

async function setArchived(fundaId: string, action: "archive" | "restore"): Promise<Listing> {
  const response = await fetch(`/api/listings/${fundaId}/${action}`, { method: "POST" });
  if (!response.ok) throw new Error(`${action} unavailable`);
  return response.json();
}

export const archiveListing = (fundaId: string) => setArchived(fundaId, "archive");
export const restoreListing = (fundaId: string) => setArchived(fundaId, "restore");

async function post(path: string, body?: unknown): Promise<Listing | CaptureError> {
  try {
    const response = await fetch(path, {
      method: "POST",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
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
    const response = await fetch("/api/listings/manual", { method: "POST", body: form });
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

export type SourceFact = {
  key: string;
  value: string | number;
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
  page: number;
  provenance: "finding";
  seller_stated: true;
  document_id: number;
  document_name: string;
  extracted_at: string;
};

export type CaseFact = ListingFact | SourceFact | FindingFact;

export type DocumentStatus = "pending" | "analysed" | "unreadable" | "not_analysed" | "download_failed";

/** A Document as the Case lists it. */
export type CaseDocument = {
  id: number;
  name: string;
  kind: "upload" | "brochure";
  status: DocumentStatus;
  reason: string | null;
  page_count: number | null;
  finding_count: number;
  rejected_findings: number;
  added_at: string;
  extracted_at: string | null;
};

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
  max_price: number;
  provenance: "computed";
  computed_on: string;
};

export type Evidence = {
  key: string;
  value: string | number | boolean | null;
  provenance: string;
  fetched_at?: string | null;
  /** Findings only: the Document and page the evidence is on. */
  page?: number;
  document_id?: number;
  document_name?: string;
  statement?: string;
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
    documents: { id: number; sha256: string | null; status: DocumentStatus }[];
  };
  facts: CaseFact[];
  sources: SourceStatus[];
  documents: CaseDocument[];
  metrics: Metrics;
  affordability: Affordability | null;
  flags: Flag[];
  hard_no: HardNo | null;
  rules: { year: number; is_current_year: boolean };
};

export async function fetchCase(fundaId: string): Promise<Case> {
  const response = await fetch(`/api/listings/${fundaId}/case`);
  if (!response.ok) throw new Error("case unavailable");
  return response.json();
}

/** Manually refetch one Source; returns the rebuilt Case. Nothing refetches by itself. */
export async function refetchSource(fundaId: string, source: string): Promise<Case> {
  const response = await fetch(`/api/listings/${fundaId}/sources/${source}/refetch`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("source refetch unavailable");
  return response.json();
}

const documentsPath = (fundaId: string) => `/api/listings/${fundaId}/documents`;

async function sendDocument(path: string, method: "POST" | "PUT", file: File): Promise<void> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(path, { method, body: form });
  if (!response.ok) throw new Error("document upload failed");
}

/** Upload a Document; its Findings are extracted before this resolves. */
export const uploadDocument = (fundaId: string, file: File) =>
  sendDocument(documentsPath(fundaId), "POST", file);

/** Re-upload: the file replaces the Document and its Findings. */
export const replaceDocument = (fundaId: string, documentId: number, file: File) =>
  sendDocument(`${documentsPath(fundaId)}/${documentId}`, "PUT", file);

export async function removeDocument(fundaId: string, documentId: number): Promise<void> {
  const response = await fetch(`${documentsPath(fundaId)}/${documentId}`, { method: "DELETE" });
  if (!response.ok) throw new Error("document removal failed");
}

/** Retry a Document that was not analysed, or a brochure whose download failed. */
export async function analyseDocument(fundaId: string, documentId: number): Promise<void> {
  const response = await fetch(`${documentsPath(fundaId)}/${documentId}/analyse`, { method: "POST" });
  if (!response.ok) throw new Error("document analysis failed");
}

/** The Document itself, served only to this app; `page` opens it at that page. */
export const documentFileUrl = (fundaId: string, documentId: number, page?: number) =>
  `${documentsPath(fundaId)}/${documentId}/file${page ? `#page=${page}` : ""}`;

/** What changed since a Verdict was made; any entry makes it out of date (Achterhaald). */
export type VerdictInput = "case" | "buyer_profile" | "rules" | "model";

export type BidAdvice = {
  opening_bid: number;
  walk_away_maximum: number;
  conditions: string[];
  affordable_maximum: number;
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
  const response = await fetch(`/api/listings/${fundaId}/verdict`);
  if (!response.ok) throw new Error("verdict unavailable");
  return response.json();
}

/** Ask for a new Verdict version. Never happens by itself. */
export async function runVerdict(fundaId: string): Promise<Verdict | VerdictError> {
  try {
    const response = await fetch(`/api/listings/${fundaId}/verdict`, { method: "POST" });
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
  const response = await fetch("/api/verdicts/out-of-date");
  if (!response.ok) throw new Error("out-of-date verdicts unavailable");
  return response.json();
}
