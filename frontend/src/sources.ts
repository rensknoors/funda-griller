import { plural } from "./plural";

const SOURCE_LABELS: Record<string, string> = {
  energielabel: "Energielabelregister",
  woz: "WOZ (prijshistorie)",
  flood_soil: "Overstroming en bodem",
  noise: "Geluid",
  comparables: "Vergelijkbare verkopen",
  commute: "Reistijd",
};

export const sourceLabel = (source: string) => SOURCE_LABELS[source] ?? source;

/** "1 feit verouderd", "3 feiten verouderd": the Stale chip, so it never reads as the Oordeel. */
export const staleLabel = (count: number) => `${plural(count, "feit", "feiten")} verouderd`;
