import { Ban, Check, Circle, CircleDashed, Minus } from "lucide-react";

import { TIER_LABEL, type TierKey } from "./comparison";

/** Each tier has its own shape, so it reads in greyscale: tick, ring, dashed ring, dash, ban. */
const TIER_ICON: Record<TierKey, typeof Check> = {
  must_buy: Check,
  consider: Circle,
  none: CircleDashed,
  skip: Minus,
  hard_no: Ban,
};

/** A Verdict tier as glyph and label: inline in lists, compact in filters, large on the Oordeel. */
export function TierMark({ tier, size = "inline" }: { tier: TierKey; size?: "inline" | "compact" | "large" }) {
  const Icon = TIER_ICON[tier];
  if (size === "large") {
    return (
      <span className={`tier-mark tier-${tier}`}>
        <span className="tier-glyph" aria-hidden="true">
          <Icon size={26} strokeWidth={2.25} />
        </span>
        <span className="tier-label">{TIER_LABEL[tier]}</span>
      </span>
    );
  }
  return (
    <span className={`tier tier-${tier}${size === "compact" ? " compact" : ""}`}>
      <span aria-hidden="true" className="tier-glyph">
        <Icon size={13} strokeWidth={2.5} />
      </span>
      {TIER_LABEL[tier]}
    </span>
  );
}
