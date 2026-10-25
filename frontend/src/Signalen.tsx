/** Signalen: the Flags grouped as pros, cons and risks, each expandable to its rule and evidence,
 * and the Harde afwijzing banner when a deal-breaker is hit. */

import type { CaseFact, Evidence, Flag, FlagClass, FindingFact, HardNo } from "./api";
import { FINDING_LABELS } from "./Documenten";
import { ENVIRONMENT_FACTS, FACT_LABELS, PROVENANCE_LABELS, commuteText, formatNumber } from "./facts";
import { OBSERVATION_LABELS, observationValue, photoList } from "./FotoWaarnemingen";

const EVIDENCE_LABELS: Record<string, string> = {
  ...FACT_LABELS,
  woz_value: "WOZ-waarde",
  asking_vs_woz: "Vraagprijs gedeeld door WOZ",
  asking_vs_comparables_percent: "Vraagprijs per m² t.o.v. vergelijkbaar",
  headroom: "Ruimte boven vraag",
  renovation_tolerance: "Verbouwtolerantie",
  worst_acceptable_energy_label: "Slechtst passende energielabel",
  ...Object.fromEntries(Object.entries(ENVIRONMENT_FACTS).map(([key, fact]) => [key, fact.label])),
  threshold: "Drempel",
  must_have: "Must-have",
  ...OBSERVATION_LABELS,
  deal_breaker: "Deal-breaker",
  named_energy_labels: "Genoemde energielabels",
  max_minutes: "Maximale reistijd",
};

const FLAG_BANDS: { flagClass: FlagClass; glyph: string; label: string }[] = [
  { flagClass: "pro", glyph: "+", label: "Pluspunt" },
  { flagClass: "con", glyph: "−", label: "Minpunt" },
  { flagClass: "risk", glyph: "!", label: "Risico" },
];

export function HardNoBanner({ hardNo, flags }: { hardNo: HardNo; flags: Flag[] }) {
  const cause = flags.find((flag) => flag.id === hardNo.flag_id);
  return (
    <div role="status" className="hard-no">
      <span className="hard-no-mark" aria-hidden="true">✕</span>
      <div>
        <p className="hard-no-tier">Harde afwijzing</p>
        <p>
          Deal-breaker: <strong>{hardNo.deal_breaker}</strong>
          {cause && <> · {cause.title}</>}
        </p>
        <p className="muted">Deterministisch toegepast, geen model gebruikt.</p>
      </div>
    </div>
  );
}

export function signaalAnchor(flagId: string): string {
  return `signaal-${flagId.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}

export function Signalen({
  flags,
  facts,
  rulesVersion,
  focusFlagId,
}: {
  flags: Flag[];
  facts: CaseFact[];
  rulesVersion: number;
  focusFlagId: string | null;
}) {
  return (
    <section aria-labelledby="signalen-title">
      <h3 id="signalen-title">Signalen</h3>
      {flags.length === 0 && <p className="empty">Geen signalen bij deze woning volgens regelset {rulesVersion}.</p>}
      {FLAG_BANDS.map((band) => {
        const inBand = flags.filter((flag) => flag.class === band.flagClass);
        if (inBand.length === 0) return null;
        return (
          <div key={band.flagClass} className={`flag-band flag-${band.flagClass}`}>
            <h4>
              <span className="flag-glyph" aria-hidden="true">{band.glyph}</span> {band.label} ({inBand.length})
            </h4>
            <ul className="flags">
              {inBand.map((flag) => (
                <li key={flag.id} id={signaalAnchor(flag.id)} className={flag.id === focusFlagId ? "focused" : undefined}>
                  <details open={flag.id === focusFlagId || undefined}>
                    <summary>{flag.title}</summary>
                    <p className="muted">
                      Regel {flag.rule_id} · versie {flag.rule_version}
                    </p>
                    <ul className="evidence">
                      {flag.evidence.map((item) => (
                        <EvidenceRow key={item.key} item={item} facts={facts} />
                      ))}
                    </ul>
                  </details>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </section>
  );
}

function EvidenceRow({ item, facts }: { item: Evidence; facts: CaseFact[] }) {
  if (item.provenance === "finding") {
    return (
      <li>
        {FINDING_LABELS[item.key as FindingFact["key"]] ?? item.key}: <strong>“{item.statement}”</strong>{" "}
        <span className="muted">
          ({PROVENANCE_LABELS.finding}, {item.document_name} p. {item.page})
        </span>{" "}
        <a href="#verkoper-informatie-title">Zie verkoper-informatie</a>
      </li>
    );
  }
  // Only Kenmerken rows carry a vak anchor; Source facts are shown in their own groups.
  const vak =
    item.provenance === "listing"
      ? facts.findIndex((fact) => fact.key === item.key && fact.provenance === "listing") + 1
      : 0;
  return (
    <li>
      {evidenceLabel(item)}:<strong>{evidenceValue(item)}</strong>{" "}
      <span className="muted">
        ({PROVENANCE_LABELS[item.provenance] ?? item.provenance}
        {item.photos && item.photos.length > 0 && <>, foto {photoList(item.photos)}</>})
      </span>
      {vak > 0 && (
        <>
          {" "}
          <a href={`#vak-${vak}`}>Zie vak {vak}</a>
        </>
      )}
    </li>
  );
}

function evidenceLabel(item: Evidence): string {
  const key = item.key;
  if (item.commute) return `Reistijd naar ${item.commute.destination}`;
  if (key.endsWith("_mentioned")) return `‘${key.slice(0, -"_mentioned".length)}’ genoemd in advertentie`;
  return EVIDENCE_LABELS[key] ?? key;
}

function evidenceValue(item: Evidence): string {
  if (item.provenance === "observation") return observationValue(item.key, item.value);
  if (item.commute) return commuteText(item.commute);
  if (typeof item.value === "boolean") return item.value ? "ja" : "nee";
  if (item.value === null) return "–";
  if (Array.isArray(item.value)) return item.value.join(", ");
  if (typeof item.value === "number") return formatNumber(item.key, item.value);
  return String(item.value);
}
