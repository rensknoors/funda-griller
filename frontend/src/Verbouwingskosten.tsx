/** Verbouwingskosten: the Verbouwingsraming in three urgency classes, each item a geschatte
 * euro range citing the facts that triggered it, as in Signalen. */

import type { CaseFact, RenovationEstimate, RenovationInput, RenovationItem, Urgency } from "./api";
import { euro, euroRange } from "./format";
import { plural } from "./plural";
import { EvidenceRow } from "./Signalen";
import { Stamp } from "./Stamp";

export const URGENCY_LABELS: Record<Urgency, string> = {
  direct: "Direct nodig",
  within_5_years: "Binnen 5 jaar",
  optional: "Optioneel",
};

const MISSING_LABELS: Record<RenovationInput, string> = {
  observations: "geen foto-waarnemingen",
  vragenlijst: "geen Vragenlijst",
  energielabel: "geen energielabel",
};

export function Verbouwingskosten({ estimate, facts }: { estimate: RenovationEstimate; facts: CaseFact[] }) {
  const years = [...new Set(estimate.items.map((item) => item.price_year))].sort();
  const direct = estimate.classes.direct;
  return (
    <details open className="fact-group verbouwingskosten">
      <summary>
        <h2 id="verbouwingskosten-title">Verbouwingskosten</h2>
        <span className="muted">
          {plural(estimate.items.length, "post", "posten")}
          {years.length > 0 && ` · prijspeil ${years.join(", ")}`}
        </span>
      </summary>
      {estimate.missing_inputs.length > 0 && (
        <p className="empty">
          Niet meegenomen: {estimate.missing_inputs.map((input) => MISSING_LABELS[input]).join(", ")}. Posten die
          daaruit zouden volgen, ontbreken.
        </p>
      )}
      {estimate.items.length === 0 ? (
        <p className="empty">Geen verbouwingsposten gevonden in de feiten van deze woning.</p>
      ) : (
        (Object.keys(URGENCY_LABELS) as Urgency[]).map((urgency) => {
          const items = estimate.items.filter((item) => item.urgency === urgency);
          if (items.length === 0) return null;
          const total = estimate.classes[urgency];
          return (
            <div key={urgency} className={`urgency-band urgency-${urgency}`}>
              <h3>
                {URGENCY_LABELS[urgency]}: <span className="num">{euroRange(total.low, total.high)}</span>
              </h3>
              <ul className="flags">
                {items.map((item) => (
                  <RenovationRow key={item.id} item={item} facts={facts} />
                ))}
              </ul>
            </div>
          );
        })
      )}
      {direct.midpoint > 0 && (
        <p className="muted">
          Het midden van Direct nodig, {euro.format(direct.midpoint)}, is afgetrokken van je betaalruimte en van de
          basis van het maximumbod. Gelijk voor elk koperprofiel; kostentabel versie {estimate.cost_table_version}.
        </p>
      )}
    </details>
  );
}

function RenovationRow({ item, facts }: { item: RenovationItem; facts: CaseFact[] }) {
  const notes = [
    item.inspection && "onderzoek op basis van bouwjaar",
    item.size_assumed && "woonoppervlak onbekend, middelgrote woning aangenomen",
  ].filter(Boolean);
  return (
    <li>
      <details>
        <summary>
          {item.label}: <strong className="num">{euroRange(item.low, item.high)}</strong>{" "}
          <Stamp kind="computed" label={`Geschat, prijspeil ${item.price_year}, bron ${item.source}`}>
            Geschat · prijspeil {item.price_year}
          </Stamp>
          {notes.length > 0 && <span className="muted"> ({notes.join("; ")})</span>}
        </summary>
        <p className="muted">Bron prijzen: {item.source}</p>
        <ul className="evidence">
          {item.evidence.map((evidence, index) => (
            <EvidenceRow key={`${evidence.key}-${index}`} item={evidence} facts={facts} />
          ))}
        </ul>
      </details>
    </li>
  );
}
