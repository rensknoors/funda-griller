import { useEffect, useState } from "react";

import {
  type Affordability,
  type Case,
  type CaseFact,
  type Evidence,
  type Flag,
  type FlagClass,
  type HardNo,
  type Listing,
  fetchCase,
} from "./api";

type LoadState = { kind: "laden" } | { kind: "fout" } | { kind: "klaar"; data: Case };

const euro = new Intl.NumberFormat("nl-NL", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});
const dayMonth = new Intl.DateTimeFormat("nl-NL", { day: "numeric", month: "short" });
const shortDate = (iso: string) => dayMonth.format(new Date(iso));

const FACT_LABELS: Record<string, string> = {
  address: "Adres",
  city: "Plaats",
  status: "Status",
  asking_price: "Vraagprijs",
  living_area: "Woonoppervlak (m²)",
  plot_area: "Perceeloppervlak (m²)",
  rooms: "Kamers",
  bedrooms: "Slaapkamers",
  construction_year: "Bouwjaar",
  energy_label: "Energielabel",
  heating: "Verwarming",
};
const MONEY_FACTS = new Set(["asking_price", "headroom", "woz_value"]);

const EVIDENCE_LABELS: Record<string, string> = {
  ...FACT_LABELS,
  official_energy_label: "Energielabel (register)",
  woz_value: "WOZ-waarde",
  asking_vs_woz: "Vraagprijs gedeeld door WOZ",
  headroom: "Ruimte boven vraag",
  renovation_tolerance: "Verbouwtolerantie",
  worst_acceptable_energy_label: "Slechtst passende energielabel",
  threshold: "Drempel",
  must_have: "Must-have",
  deal_breaker: "Deal-breaker",
};

const PROVENANCE_LABELS: Record<string, string> = {
  listing: "Advertentie",
  source: "Bron",
  computed: "Berekend",
  buyer_profile: "Koperprofiel",
  rule: "Regel",
};

const FLAG_BANDS: { flagClass: FlagClass; glyph: string; label: string }[] = [
  { flagClass: "pro", glyph: "+", label: "Pluspunt" },
  { flagClass: "con", glyph: "−", label: "Minpunt" },
  { flagClass: "risk", glyph: "!", label: "Risico" },
];

function formatFact(fact: CaseFact): string {
  if (MONEY_FACTS.has(fact.key) && typeof fact.value === "number") return euro.format(fact.value);
  return String(fact.value);
}

export function CaseView(props: {
  listing: Listing;
  busy: boolean;
  onClose: () => void;
  onRefetch: (fundaId: string) => void;
}) {
  const { listing, onClose } = props;
  const [state, setState] = useState<LoadState>({ kind: "laden" });
  const latest = listing.snapshots[0];

  useEffect(() => {
    let current = true;
    setState({ kind: "laden" });
    fetchCase(listing.funda_id)
      .then((data) => current && setState({ kind: "klaar", data }))
      .catch(() => current && setState({ kind: "fout" }));
    return () => {
      current = false;
    };
  }, [listing.funda_id, latest.id]);

  return (
    <section aria-labelledby="case-title" className="dossier">
      <header className="dossier-head">
        <div>
          <h2 id="case-title">Dossier: {latest.address ?? listing.url}</h2>
          <p className="muted">
            Advertentie van {shortDate(latest.fetched_at)}
            {latest.entry === "manual" && <> · Handmatig ingevoerd</>}
            {state.kind === "klaar" && state.data.built_from.profile_version !== null && (
              <> · Koperprofiel versie {state.data.built_from.profile_version}</>
            )}
          </p>
        </div>
        <div className="row">
          <button type="button" disabled={props.busy} onClick={() => props.onRefetch(listing.funda_id)}>
            Opnieuw ophalen
          </button>
          <button type="button" onClick={onClose}>
            Terug naar woningen
          </button>
        </div>
      </header>
      {state.kind === "klaar" && state.data.hard_no && (
        <HardNoBanner hardNo={state.data.hard_no} flags={state.data.flags} />
      )}
      {state.kind === "klaar" && <KeyFigures askingPrice={latest.asking_price} affordability={state.data.affordability} />}

      {state.kind === "laden" && (
        <div className="skeleton" aria-busy="true">
          <span className="visually-hidden">Dossier laden</span>
          <div className="skeleton-row" />
          <div className="skeleton-row" />
          <div className="skeleton-row" />
        </div>
      )}
      {state.kind === "fout" && (
        <p role="alert" className="notice error">
          <span aria-hidden="true">! </span>Dossier laden mislukt. Sluit het dossier en open het
          opnieuw.
        </p>
      )}
      {state.kind === "klaar" && (
        <>
          <Signalen flags={state.data.flags} facts={state.data.facts} rulesVersion={state.data.built_from.flag_rules_version} />
          <Betaalruimte affordability={state.data.affordability} rules={state.data.rules} />
          <FactGroup facts={state.data.facts} />
        </>
      )}
    </section>
  );
}

function KeyFigures({
  askingPrice,
  affordability,
}: {
  askingPrice: number | null;
  affordability: Affordability | null;
}) {
  return (
    <dl className="figures key-figures" aria-label="Kerncijfers">
      <Figure label="Vraagprijs" value={askingPrice !== null ? euro.format(askingPrice) : "–"} />
      <Figure
        label="Ruimte boven vraag"
        value={affordability?.headroom != null ? signedEuro(affordability.headroom) : "–"}
      />
      <Figure
        label="Maandlasten bij vraagprijs"
        value={affordability?.monthly_cost != null ? `${euro.format(affordability.monthly_cost)} p/m` : "–"}
      />
    </dl>
  );
}

function Betaalruimte({
  affordability,
  rules,
}: {
  affordability: Affordability | null;
  rules: Case["rules"];
}) {
  return (
    <section aria-labelledby="betaalruimte-title">
      <h3 id="betaalruimte-title">Betaalruimte</h3>
      {affordability === null ? (
        <p className="empty">
          Vul je koperprofiel in om je budget bij deze woning te zien: maximale hypotheek,
          kosten koper en ruimte boven de vraagprijs.
        </p>
      ) : (
        <dl className="figures">
          <Figure label="Maximale hypotheek" value={euro.format(affordability.max_mortgage)}>
            {affordability.energy_label_bonus > 0 &&
              `incl. ${euro.format(affordability.energy_label_bonus)} voor energielabel`}
          </Figure>
          <Figure label="Overwaarde eigen woning" value={euro.format(affordability.equity)} />
          <Figure
            label="Kosten koper"
            value={affordability.kosten_koper ? euro.format(affordability.kosten_koper.total) : "–"}
          >
            {affordability.kosten_koper &&
              `overdrachtsbelasting ${euro.format(affordability.kosten_koper.transfer_tax)}, vaste kosten ${euro.format(affordability.kosten_koper.fixed_costs)}`}
          </Figure>
          <Figure
            label="Maandlasten bij vraagprijs"
            value={affordability.monthly_cost !== null ? `${euro.format(affordability.monthly_cost)} p/m` : "–"}
          >
            {affordability.mortgage_needed !== null &&
              affordability.mortgage_needed > affordability.max_mortgage &&
              "! hypotheek nodig is hoger dan de maximale hypotheek"}
          </Figure>
          <Figure
            label="Ruimte boven vraag"
            value={affordability.headroom !== null ? signedEuro(affordability.headroom) : "–"}
          />
        </dl>
      )}
      <p className="muted rules-year">
        Regels {rules.year}
        {!rules.is_current_year && (
          <>
            {" "}
            <span className="chip">Achterhaald</span> regels zijn niet van dit jaar
          </>
        )}
      </p>
    </section>
  );
}

function signedEuro(amount: number): string {
  if (amount === 0) return euro.format(0);
  return `${amount > 0 ? "▲ +" : "▼ "}${euro.format(amount)}`;
}

function Figure(props: { label: string; value: string; children?: React.ReactNode }) {
  return (
    <div className="figure">
      <dt>{props.label}</dt>
      <dd className="num">{props.value}</dd>
      {props.children && <dd className="muted note">{props.children}</dd>}
    </div>
  );
}

function FactGroup({ facts }: { facts: CaseFact[] }) {
  return (
    <details open className="fact-group">
      <summary>
        <h3 id="feiten-title">Kenmerken</h3>
        <span className="muted">{facts.length} feiten</span>
      </summary>
      <ol className="facts">
        {facts.map((fact, index) => (
          <li key={fact.key} id={`vak-${index + 1}`} className="fact">
            <span className="vak-number">{index + 1}</span>
            <span className="fact-label">{FACT_LABELS[fact.key] ?? fact.key}</span>
            <span className="fact-value">{formatFact(fact)}</span>
            <span className="stamp" aria-label={`Bron: advertentie, opgehaald ${shortDate(fact.fetched_at)}`}>
              <span aria-hidden="true">■ ADV</span> Advertentie · {shortDate(fact.fetched_at)}
            </span>
          </li>
        ))}
      </ol>
    </details>
  );
}

function HardNoBanner({ hardNo, flags }: { hardNo: HardNo; flags: Flag[] }) {
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

function Signalen({ flags, facts, rulesVersion }: { flags: Flag[]; facts: CaseFact[]; rulesVersion: number }) {
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
                <li key={flag.id}>
                  <details>
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
  const vak = facts.findIndex((fact) => fact.key === item.key) + 1;
  return (
    <li>
      {evidenceLabel(item.key)}: <strong>{evidenceValue(item)}</strong>{" "}
      <span className="muted">({PROVENANCE_LABELS[item.provenance] ?? item.provenance})</span>
      {vak > 0 && (
        <>
          {" "}
          <a href={`#vak-${vak}`}>Zie vak {vak}</a>
        </>
      )}
    </li>
  );
}

function evidenceLabel(key: string): string {
  if (key.endsWith("_mentioned")) return `‘${key.slice(0, -"_mentioned".length)}’ genoemd in advertentie`;
  return EVIDENCE_LABELS[key] ?? key;
}

function evidenceValue(item: Evidence): string {
  if (typeof item.value === "boolean") return item.value ? "ja" : "nee";
  if (item.value === null) return "–";
  if (MONEY_FACTS.has(item.key) && typeof item.value === "number") return euro.format(item.value);
  return String(item.value);
}
