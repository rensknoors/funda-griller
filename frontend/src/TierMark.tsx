import { TIER_GLYPH, TIER_LABEL, type TierKey } from "./comparison";

/** A Verdict tier as glyph and label: inline in lists, compact in filters, large on the Oordeel. */
export function TierMark({ tier, size = "inline" }: { tier: TierKey; size?: "inline" | "compact" | "large" }) {
  if (size === "large") {
    return (
      <span className={`tier-mark tier-${tier}`}>
        <span className="tier-glyph" aria-hidden="true">
          {TIER_GLYPH[tier]}
        </span>
        <span className="tier-label">{TIER_LABEL[tier]}</span>
      </span>
    );
  }
  return (
    <span className={`tier tier-${tier}${size === "compact" ? " compact" : ""}`}>
      <span aria-hidden="true" className="tier-glyph">
        {TIER_GLYPH[tier]}
      </span>{" "}
      {TIER_LABEL[tier]}
    </span>
  );
}
