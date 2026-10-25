/** Dutch number formats shared by every screen, so one amount reads the same everywhere. */

export const euro = new Intl.NumberFormat("nl-NL", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

export const decimal = new Intl.NumberFormat("nl-NL", { maximumFractionDigits: 2 });

/** A change in percent with its sign and at most one decimal: "+51,8", "-6,8", "0". */
export const percentChange = new Intl.NumberFormat("nl-NL", { maximumFractionDigits: 1, signDisplay: "exceptZero" });

/** A percentage difference with a direction arrow: "▲ +51,8%", "▼ -6,8%", "= 0%"; "–" when unknown. */
export function signedPercent(value: number | null): string {
  if (value === null) return "–";
  return `${value > 0 ? "▲" : value < 0 ? "▼" : "="} ${percentChange.format(value)}%`;
}

/** An amount above or below zero with a direction arrow: "▲ +€ 109.519", "▼ −€ 5.000", "€ 0". */
export function signedEuro(amount: number): string {
  if (amount === 0) return euro.format(0);
  return `${amount > 0 ? "▲ +" : "▼ −"}${euro.format(Math.abs(amount))}`;
}
