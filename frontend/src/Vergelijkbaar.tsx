import type { AskingVsComparables, Comparable, SourceFact, SourceStatus } from "./api";

const euro = new Intl.NumberFormat("nl-NL", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
const percent = new Intl.NumberFormat("nl-NL", { maximumFractionDigits: 1, signDisplay: "exceptZero" });
const dayMonth = new Intl.DateTimeFormat("nl-NL", { day: "numeric", month: "short" });

/** "t.o.v. vergelijkbaar" as a short figure, for the header strip and the list. */
export function comparablesFigure(metric: AskingVsComparables): string {
  if (metric.percent === null) return "–";
  const arrow = metric.percent > 0 ? "▲ " : metric.percent < 0 ? "▼ " : "";
  return `${arrow}${percent.format(metric.percent)}%`;
}

/** Plain statement of how much the comparables can carry; thin or missing is said, never hidden. */
export function coverageNote(metric: Pick<AskingVsComparables, "coverage" | "count">): string {
  switch (metric.coverage) {
    case "not_fetched":
      return "Nog niet opgehaald";
    case "none":
      return "Geen vergelijkbare woningen gevonden";
    case "thin":
      return `Dun: maar ${metric.count} vergelijkbare ${metric.count === 1 ? "woning" : "woningen"}`;
    case "sufficient":
      return `${metric.count} vergelijkbare woningen`;
  }
}

/**
 * Dossier group for comparables: nearby Listings from funda's "vergelijkbare woningen", fetched
 * only when the user asks (one fetch per woning, capped), and the asking price per m² against them.
 */
export function Vergelijkbaar(props: {
  metric: AskingVsComparables;
  facts: SourceFact[];
  status: SourceStatus | undefined;
  refetching: string | null;
  onFetch: () => void;
}) {
  const { metric } = props;
  const comparables = props.facts.filter((f) => f.key === "comparable");
  const stale = comparables.some((f) => f.stale);
  const fetchedAt = comparables[0]?.fetched_at ?? null;
  return (
    <details open className="fact-group">
      <summary>
        <h3 id="vergelijkbaar-title">Vergelijkbare woningen</h3>
        <span className="muted">
          {coverageNote(metric)}
          {stale && " · verouderd"}
        </span>
      </summary>
      <div className="row">
        <button type="button" className="small" disabled={props.refetching !== null} onClick={props.onFetch}>
          {props.refetching === "comparables"
            ? "Bezig…"
            : metric.coverage === "not_fetched"
              ? "Vergelijkbare woningen ophalen"
              : "Opnieuw ophalen"}
        </button>
        <span className="muted">Haalt een klein, vast aantal woningen op, alleen op jouw verzoek.</span>
      </div>
      {props.status?.status === "failed" && (
        <p className="empty">
          <span aria-hidden="true">✕ </span>Bron mislukt, geen gegevens van vergelijkbare woningen.
        </p>
      )}
      {(metric.coverage === "none" || metric.coverage === "thin") && (
        <p className="empty" role="note">
          <span aria-hidden="true">! </span>
          {coverageNote(metric)}. Te weinig om het Maximumbod op te baseren
          {metric.coverage === "thin" && ` (minimaal ${metric.min_count})`}; dat volgt alleen je betaalruimte.
        </p>
      )}
      <ol className="facts">
        {metric.percent !== null && metric.median_price_per_m2 !== null && (
          <li className="fact">
            <span className="vak-number">=</span>
            <span className="fact-label">Vraagprijs per m² t.o.v. vergelijkbaar</span>
            <span className="fact-value">
              {percent.format(metric.percent)}% ({euro.format(metric.price_per_m2 ?? 0)} tegen mediaan{" "}
              {euro.format(metric.median_price_per_m2)} per m²)
            </span>
            <span className="stamp stamp-computed" aria-label={`Berekend uit ${metric.count} vergelijkbare woningen`}>
              <span aria-hidden="true">= BER</span> Berekend · {metric.count} woningen
            </span>
          </li>
        )}
        {metric.comparables_value !== null && (
          <li className="fact">
            <span className="vak-number">=</span>
            <span className="fact-label">Waarde volgens vergelijkbaar</span>
            <span className="fact-value">{euro.format(metric.comparables_value)}</span>
            <span className="stamp stamp-computed" aria-label="Berekend: mediaan per m² maal woonoppervlak">
              <span aria-hidden="true">= BER</span> Berekend · mediaan × m²
            </span>
          </li>
        )}
        {comparables.map((fact, index) => {
          const c = fact.value as Comparable;
          return (
            <li key={c.funda_id} className="fact comparable">
              <span className="vak-number">{index + 1}</span>
              <span className="fact-label">
                {c.url ? (
                  <a href={c.url} target="_blank" rel="noreferrer">
                    {c.address ?? c.funda_id}
                  </a>
                ) : (
                  (c.address ?? c.funda_id)
                )}
                {c.city && <span className="muted">, {c.city}</span>}
              </span>
              <span className="fact-value">
                {c.asking_price != null ? euro.format(c.asking_price) : "–"}
                {" · "}
                {c.living_area != null ? `${c.living_area} m²` : "– m²"}
                {c.asking_price != null && c.living_area != null && c.living_area > 0 && (
                  <span className="muted"> · {euro.format(Math.round(c.asking_price / c.living_area))}/m²</span>
                )}
              </span>
              <span
                className="stamp"
                aria-label={`Bron: funda vergelijkbare woningen, ${c.recently_sold ? "recent verkocht" : "recent te koop gezet"}, opgehaald ${fetchedAt ? dayMonth.format(new Date(fetchedAt)) : ""}`}
              >
                <span aria-hidden="true">⇄ VGL</span> {c.recently_sold ? "Recent verkocht" : "Recent te koop"}
                {c.raw_status && ` (${c.raw_status})`} · laatste vraagprijs
                {fact.stale && " · verouderd"}
              </span>
            </li>
          );
        })}
      </ol>
    </details>
  );
}
