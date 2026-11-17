import type { AskingVsExpected, ExpectedSalePrice, Metrics } from "./api";
import { euro, euroRange } from "./format";
import { coverageNote } from "./Vergelijkbaar";

const percentFormat = new Intl.NumberFormat("nl-NL", { maximumFractionDigits: 1 });

/** "Vraagprijs 8% boven verwachte verkoopprijs", or "gelijk aan" when they meet. */
export function askingAgainstExpected(prijsstelling: AskingVsExpected): string {
  if (prijsstelling.percent === 0) return "Vraagprijs gelijk aan verwachte verkoopprijs";
  const direction = prijsstelling.percent > 0 ? "boven" : "onder";
  return `Vraagprijs ${percentFormat.format(Math.abs(prijsstelling.percent))}% ${direction} verwachte verkoopprijs`;
}

/** How the figure was reached, in words the buyer can check. */
function basisText(expected: ExpectedSalePrice, metrics: Metrics): string {
  if (expected.basis === "comparables" && expected.overbid) {
    const count = metrics.asking_vs_comparables.count;
    return `op basis van ${count} vergelijkbare woningen, incl. ${percentFormat.format(expected.overbid.value * 100)}% gemiddeld overbod`;
  }
  return "op basis van de WOZ-waarde naar vandaag";
}

/**
 * Dossier block: what the house is expected to sell for, how that was reached, and how the seller
 * priced it against that. Without evidence it says so and how to get some, never the asking price.
 */
export function VerwachteVerkoopprijs({ metrics }: { metrics: Metrics }) {
  const expected = metrics.expected_sale_price;
  const prijsstelling = metrics.asking_vs_expected;
  const comparables = metrics.asking_vs_comparables;
  return (
    <section aria-labelledby="verwachte-verkoopprijs-title">
      <h2 id="verwachte-verkoopprijs-title">Verwachte verkoopprijs</h2>
      {expected.value === null ? (
        <p className="empty">
          Te weinig gegevens om de prijs te beoordelen: geen WOZ-waarde en te weinig vergelijkbare woningen.{" "}
          <a href="#vergelijkbaar-title">Haal vergelijkbare woningen op</a> om de verkoopprijs te schatten.
        </p>
      ) : (
        <dl className="figures">
          <div className="figure">
            <dt>Verwachte verkoopprijs</dt>
            <dd className="num">{euro.format(expected.value)}</dd>
            <dd className="muted note">{basisText(expected, metrics)}</dd>
            {expected.weakly_grounded && (
              <dd className="note">
                <span className="chip">Zwak onderbouwd</span>
              </dd>
            )}
            {expected.weakly_grounded && comparables.coverage === "thin" && (
              <dd className="muted note">{coverageNote(comparables)}: tellen niet mee.</dd>
            )}
          </div>
          {expected.low !== null && expected.high !== null && expected.low !== expected.high && (
            <div className="figure">
              <dt>Bandbreedte</dt>
              <dd className="num">{euroRange(expected.low, expected.high)}</dd>
              <dd className="muted note">de middelste helft van de vergelijkbare woningen</dd>
            </div>
          )}
          {prijsstelling && (
            <div className="figure">
              <dt>Prijsstelling</dt>
              <dd>{prijsstelling.prijsstelling}</dd>
              <dd className="muted note">{askingAgainstExpected(prijsstelling)}</dd>
            </div>
          )}
        </dl>
      )}
    </section>
  );
}
