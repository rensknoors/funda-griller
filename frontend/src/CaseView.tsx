import { useEffect, useState } from "react";

import { type Affordability, type Case, type CaseFact, type Listing, fetchCase } from "./api";

type LoadState = { kind: "laden" } | { kind: "fout" } | { kind: "klaar"; data: Case };

const euro = new Intl.NumberFormat("nl-NL", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});
const date = new Intl.DateTimeFormat("nl-NL", { day: "numeric", month: "short" });

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
const MONEY_FACTS = new Set(["asking_price"]);

function formatFact(fact: CaseFact): string {
  if (MONEY_FACTS.has(fact.key) && typeof fact.value === "number") return euro.format(fact.value);
  return String(fact.value);
}

export function CaseView({ listing, onClose }: { listing: Listing; onClose: () => void }) {
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
            Advertentie van {date.format(new Date(latest.fetched_at))}
            {state.kind === "klaar" && state.data.built_from.profile_version !== null && (
              <> · Koperprofiel versie {state.data.built_from.profile_version}</>
            )}
          </p>
        </div>
        <button type="button" onClick={onClose}>
          Terug naar woningen
        </button>
      </header>

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
          <Betaalruimte affordability={state.data.affordability} rules={state.data.rules} />
          <FactGroup facts={state.data.facts} />
        </>
      )}
    </section>
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
          />
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
            <span className="chip">Verouderd</span> tabel is niet van dit jaar
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
    <section aria-labelledby="feiten-title">
      <h3 id="feiten-title">Kenmerken</h3>
      <p className="muted">{facts.length} feiten · 0 verouderd · 0 geschat</p>
      <ol className="facts">
        {facts.map((fact, index) => (
          <li key={fact.key} className="fact">
            <span className="vak-number">{index + 1}</span>
            <span className="fact-label">{FACT_LABELS[fact.key] ?? fact.key}</span>
            <span className="fact-value">{formatFact(fact)}</span>
            <span className="stamp" aria-label={`Bron: advertentie, opgehaald ${date.format(new Date(fact.fetched_at))}`}>
              <span aria-hidden="true">■ ADV</span> Advertentie · {date.format(new Date(fact.fetched_at))}
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}
