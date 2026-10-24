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

export type CaseFact = ListingFact | SourceFact;

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
  provenance: "computed";
  computed_on: string;
};

export type Evidence = {
  key: string;
  value: string | number | boolean | null;
  provenance: string;
  fetched_at?: string | null;
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
  built_from: { snapshot_id: number; profile_version: number | null; flag_rules_version: number };
  facts: CaseFact[];
  sources: SourceStatus[];
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
