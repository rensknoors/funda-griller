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
  price_history: { date: string | null; price: number | null }[];
};

export type Listing = {
  funda_id: string;
  url: string;
  snapshots: Snapshot[];
};

export type CaptureError =
  | { kind: "bad_url" }
  | { kind: "listing_removed" }
  | { kind: "provider_blocked" }
  | { kind: "already_captured"; fundaId: string }
  | { kind: "unknown" };

export async function fetchListings(): Promise<Listing[]> {
  const response = await fetch("/api/listings");
  if (!response.ok) throw new Error("listings unavailable");
  return response.json();
}

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

export type Case = {
  funda_id: string;
  built_from: { snapshot_id: number; profile_version: number | null };
  facts: CaseFact[];
  sources: SourceStatus[];
  metrics: Metrics;
  affordability: Affordability | null;
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
