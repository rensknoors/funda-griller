/** How Case facts are labelled and shown: the Dutch label per fact key, the herkomst word per
 * provenance class, and number formats per kind of fact. */

import type { CaseFact, CommuteFact, CommuteMode, CommuteUnknown } from "./api";
import { decimal, euro, percentChange } from "./format";
import { statusLabel } from "./ListingsTable";

export const FACT_LABELS: Record<string, string> = {
  address: "Adres",
  city: "Plaats",
  status: "Status",
  asking_price: "Vraagprijs",
  living_area: "Woonoppervlak (m²)",
  plot_area: "Perceeloppervlak (m²)",
  rooms: "Kamers",
  bedrooms: "Slaapkamers",
  construction_year: "Bouwjaar",
  energy_label: "Energielabel",
  heating: "Verwarming",
  ownership_situation: "Eigendomssituatie",
};
const MONEY_FACTS = new Set(["asking_price", "headroom", "woz_value"]);

// Flood, soil and noise Source facts: label and how to show the number.
export const ENVIRONMENT_FACTS: Record<string, { label: string; format: (value: number) => string }> = {
  flood_depth_m: {
    label: "Waterdiepte bij overstroming (kleine kans)",
    format: (v) => `${decimal.format(v)} m`,
  },
  subsidence_mm_per_year: {
    label: "Bodemdaling",
    format: (v) => `${decimal.format(v)} mm per jaar`,
  },
  pile_rot_risk_pct: {
    label: "Risico op paalrot in de buurt",
    format: (v) => `${decimal.format(v)}% van de panden`,
  },
  lden_all_sources_db: { label: "Geluid, alle bronnen (Lden)", format: (v) => `${v} dB` },
  lden_road_db: { label: "Geluid, wegverkeer (Lden)", format: (v) => `${v} dB` },
  lden_rail_db: { label: "Geluid, treinverkeer (Lden)", format: (v) => `${v} dB` },
  lden_air_db: { label: "Geluid, vliegverkeer (Lden)", format: (v) => `${v} dB` },
};

export const PROVENANCE_LABELS: Record<string, string> = {
  listing: "Advertentie",
  source: "Bron",
  computed: "Berekend",
  finding: "Bevinding, door verkoper",
  buyer_profile: "Koperprofiel",
  rule: "Regel",
  observation: "Waarneming, geschat",
};

export function formatNumber(key: string, value: number): string {
  if (MONEY_FACTS.has(key)) return euro.format(value);
  if (key === "threshold") return decimal.format(value);
  if (key === "max_minutes") return `${value} min`;
  if (key === "asking_vs_comparables_percent") return `${percentChange.format(value)}%`;
  return ENVIRONMENT_FACTS[key]?.format(value) ?? String(value);
}

const MODE_LABELS: Record<CommuteMode, string> = { car: "auto", bike: "fiets" };

const COMMUTE_UNAVAILABLE: Record<CommuteUnknown["unavailable"], string> = {
  destination_not_found: "adres niet gevonden",
  no_route: "geen route gevonden",
};

/** A commute travel time with the modes stated: "38 min met de auto (fiets 95 min), openbaar
 * vervoer niet meegerekend"; or why it is unknown. */
export function commuteText(travel: CommuteFact): string {
  if (travel.minutes === null) return `onbekend: ${COMMUTE_UNAVAILABLE[travel.unavailable]}`;
  const { minutes, mode, minutes_by_mode: byMode } = travel;
  const others = (Object.keys(byMode) as CommuteMode[])
    .filter((other) => other !== mode)
    .map((other) => `${MODE_LABELS[other]} ${byMode[other]} min`);
  const rest = others.length > 0 ? ` (${others.join(", ")})` : "";
  return `${minutes} min met de ${MODE_LABELS[mode]}${rest}, openbaar vervoer niet meegerekend`;
}

export function isCommuteFact(value: unknown): value is CommuteFact {
  return typeof value === "object" && value !== null && "destination" in value && "minutes" in value;
}

export function formatValue(fact: CaseFact): string {
  if (isCommuteFact(fact.value)) return commuteText(fact.value);
  if (fact.key === "status" && typeof fact.value === "string") return statusLabel(fact.value, fact.value);
  return typeof fact.value === "number" ? formatNumber(fact.key, fact.value) : String(fact.value);
}
