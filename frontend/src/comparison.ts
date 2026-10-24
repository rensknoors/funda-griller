import type { Listing, Tier } from "./api";

export type TierKey = Tier | "none";

/** Tier order is the sort order. A Woning without an Oordeel still deserves attention, so it sits
 * above Overslaan; a Harde afwijzing always sinks to the bottom. */
export const TIER_ORDER: TierKey[] = ["must_buy", "consider", "none", "skip", "hard_no"];

export const TIER_LABEL: Record<TierKey, string> = {
  must_buy: "Zeker kopen",
  consider: "Overwegen",
  none: "Nog geen oordeel",
  skip: "Overslaan",
  hard_no: "Harde afwijzing",
};

export const TIER_GLYPH: Record<TierKey, string> = {
  must_buy: "✓",
  consider: "○",
  none: "·",
  skip: "–",
  hard_no: "✕",
};

export type SortKey = "tier" | "price" | "woz" | "area" | "headroom" | "stale";
export type Sort = { key: SortKey; direction: "ascending" | "descending" };

export type Filters = {
  tiers: TierKey[];
  minPrice: number | null;
  maxPrice: number | null;
  staleOnly: boolean;
  showArchived: boolean;
};

export const NO_FILTERS: Filters = {
  tiers: [],
  minPrice: null,
  maxPrice: null,
  staleOnly: false,
  showArchived: false,
};

export const tierOf = (listing: Listing): TierKey => listing.comparison.tier ?? "none";

const SORT_VALUE: Record<SortKey, (listing: Listing) => number | null> = {
  tier: (l) => TIER_ORDER.indexOf(tierOf(l)),
  price: (l) => l.comparison.asking_price,
  woz: (l) => l.comparison.asking_vs_woz_percent,
  area: (l) => l.comparison.living_area,
  headroom: (l) => l.comparison.headroom,
  stale: (l) => l.comparison.stale_count,
};

export function visibleListings(listings: Listing[], filters: Filters, sort: Sort): Listing[] {
  const shown = listings.filter((listing) => {
    const price = listing.comparison.asking_price;
    if (listing.archived && !filters.showArchived) return false;
    if (filters.tiers.length > 0 && !filters.tiers.includes(tierOf(listing))) return false;
    if (filters.staleOnly && listing.comparison.stale_count === 0) return false;
    if (filters.minPrice !== null && (price === null || price < filters.minPrice)) return false;
    if (filters.maxPrice !== null && (price === null || price > filters.maxPrice)) return false;
    return true;
  });
  const sign = sort.direction === "ascending" ? 1 : -1;
  // Ties fall back to tier order, then price ascending: the default view.
  const keys: [SortKey, number][] = [[sort.key, sign], ["tier", 1], ["price", 1]];
  return shown.sort((a, b) => {
    for (const [key, keySign] of keys) {
      const order = compare(SORT_VALUE[key](a), SORT_VALUE[key](b), keySign);
      if (order !== 0) return order;
    }
    return 0;
  });
}

/** Missing values sort last in either direction. */
function compare(a: number | null, b: number | null, sign: number): number {
  if (a === b) return 0;
  if (a === null) return 1;
  if (b === null) return -1;
  return (a - b) * sign;
}
