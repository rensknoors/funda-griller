/** Dutch number formats shared by every screen, so one amount reads the same everywhere. */

import type { RouteRate, RouteRates } from "./api";

export const euro = new Intl.NumberFormat("nl-NL", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

export const decimal = new Intl.NumberFormat("nl-NL", { maximumFractionDigits: 2 });

/** A change in percent with its sign and at most one decimal: "+51,8", "-6,8", "0". */
export const percentChange = new Intl.NumberFormat("nl-NL", { maximumFractionDigits: 1, signDisplay: "exceptZero" });

/** A percentage difference with its sign: "+51,8%", "-6,8%", "0%"; "–" when unknown. */
export function signedPercent(value: number | null): string {
  if (value === null) return "–";
  return `${percentChange.format(value)}%`;
}

/** An amount above or below zero with its sign: "+€ 109.519", "−€ 5.000", "€ 0". */
export function signedEuro(amount: number): string {
  if (amount === 0) return euro.format(0);
  return `${amount > 0 ? "+" : "−"}${euro.format(Math.abs(amount))}`;
}

/** "€ 3.000 – € 9.000", or one amount when low and high meet. */
export function euroRange(low: number, high: number): string {
  return low === high ? euro.format(low) : `${euro.format(low)} – ${euro.format(high)}`;
}

/** What a direction means for the buyer, so figures can carry colour beside their sign. */
export type Tone = "favorable" | "concern" | "shortfall";

/** Asking price against WOZ or comparables: above is a concern, below is in the buyer's favour. */
export function priceTone(percent: number | null | undefined): Tone | undefined {
  if (percent == null || percent === 0) return undefined;
  return percent > 0 ? "concern" : "favorable";
}

/** Room above the asking price: any room is favourable, a shortfall is not affordable. */
export function headroomTone(amount: number | null | undefined): Tone | undefined {
  if (amount == null) return undefined;
  return amount >= 0 ? "favorable" : "shortfall";
}

/** An offered rate with where it came from: "eigen rente 4,23%" or "marktrente 4,4% (2 november 2026)". */
export function rateText(rate: RouteRate): string {
  const percent = `${decimal.format(rate.rate * 100)}%`;
  return rate.source === "own" || rate.as_of === null ? `eigen rente ${percent}` : `marktrente ${percent} (${longDate(rate.as_of)})`;
}

/** Both loan routes: "met NHG eigen rente 4%; zonder NHG marktrente 4,78% (2 november 2026)". */
export function routeRatesText(rates: RouteRates): string {
  return `met NHG ${rateText(rates.nhg)}; zonder NHG ${rateText(rates.no_nhg)}`;
}

const monthYear = new Intl.DateTimeFormat("nl-NL", { month: "long", year: "numeric" });

/** An ISO date as month and year: "januari 2027". */
export function monthOf(isoDate: string): string {
  return monthYear.format(new Date(`${isoDate}T12:00:00`));
}

const dayMonthYear = new Intl.DateTimeFormat("nl-NL", { day: "numeric", month: "long", year: "numeric" });

/** An ISO date in full: "2 november 2026". */
export function longDate(isoDate: string): string {
  return dayMonthYear.format(new Date(`${isoDate}T12:00:00`));
}
