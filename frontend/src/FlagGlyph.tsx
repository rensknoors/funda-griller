import { Minus, Plus, TriangleAlert } from "lucide-react";

import type { FlagClass } from "./api";

const FLAG_ICONS: Record<FlagClass, typeof Plus> = { pro: Plus, con: Minus, risk: TriangleAlert };

/** A Flag class by shape: a round plus, a square minus, a warning triangle. */
export function FlagGlyph({ flagClass }: { flagClass: FlagClass }) {
  const Icon = FLAG_ICONS[flagClass];
  return (
    <span className={`flag-glyph flag-glyph-${flagClass}`} aria-hidden="true">
      <Icon size={flagClass === "risk" ? 15 : 12} strokeWidth={2.5} />
    </span>
  );
}
