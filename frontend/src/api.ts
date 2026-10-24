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

export type CaseFact = {
  key: string;
  value: string | number;
  provenance: "listing";
  fetched_at: string;
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
  affordability: Affordability | null;
  rules: { year: number; is_current_year: boolean };
};

export async function fetchCase(fundaId: string): Promise<Case> {
  const response = await fetch(`/api/listings/${fundaId}/case`);
  if (!response.ok) throw new Error("case unavailable");
  return response.json();
}
