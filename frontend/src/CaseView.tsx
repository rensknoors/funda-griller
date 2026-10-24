import { useEffect, useState } from "react";

import {
  type Affordability,
  type Case,
  type CaseFact,
  type Listing,
  type ListingFact,
  type Metrics,
  type SourceFact,
  type SourceStatus,
  fetchCase,
  refetchSource,
} from "./api";

type LoadState = { kind: "laden" } | { kind: "fout" } | { kind: "klaar"; data: Case };

const euro = new Intl.NumberFormat("nl-NL", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});
const dayMonth = new Intl.DateTimeFormat("nl-NL", { day: "numeric", month: "short" });
const shortDate = (iso: string) => dayMonth.format(new Date(iso));
const percent = new Intl.NumberFormat("nl-NL", { maximumFractionDigits: 1, signDisplay: "exceptZero" });

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
const MONEY_FACTS = new Set(["asking_price", "woz_value"]);

const SOURCE_LABELS: Record<string, string> = {
  energielabel: "Energielabelregister",
  woz: "WOZ (prijshistorie)",
  flood_soil: "Overstroming en bodem",
  noise: "Geluid",
  comparables: "Vergelijkbare verkopen",
};
const sourceLabel = (source: string) => SOURCE_LABELS[source] ?? source;

const STATUS_COPY: Record<SourceStatus["status"], { glyph: string; word: string }> = {
  succeeded: { glyph: "✓", word: "gelukt" },
  failed: { glyph: "✕", word: "mislukt" },
  skipped: { glyph: "–", word: "overgeslagen" },
};
const REASON_COPY: Record<string, string> = {
  no_api_key: "geen API-sleutel ingesteld",
  no_address: "adres onvolledig",
  not_fetched: "nog niet opgehaald",
};

function formatValue(fact: CaseFact): string {
  if (MONEY_FACTS.has(fact.key) && typeof fact.value === "number") return euro.format(fact.value);
  return String(fact.value);
}

function sourceFactLabel(fact: SourceFact): string {
  if (fact.key === "woz_value") return `WOZ-waarde ${fact.as_of?.slice(0, 4) ?? ""}`.trim();
  if (fact.key === "energy_label") return "Energielabel (register)";
  return FACT_LABELS[fact.key] ?? fact.key;
}

export function CaseView(props: {
  listing: Listing;
  busy: boolean;
  onClose: () => void;
  onRefetch: (fundaId: string) => void;
}) {
  const { listing, onClose } = props;
  const [state, setState] = useState<LoadState>({ kind: "laden" });
  const [refetching, setRefetching] = useState<string | null>(null);
  const [refetchFailed, setRefetchFailed] = useState(false);
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

  async function handleSourceRefetch(source: string) {
    setRefetching(source);
    setRefetchFailed(false);
    try {
      setState({ kind: "klaar", data: await refetchSource(listing.funda_id, source) });
    } catch {
      setRefetchFailed(true);
    } finally {
      setRefetching(null);
    }
  }

  const sourceFacts =
    state.kind === "klaar"
      ? state.data.facts.filter((f): f is SourceFact => f.provenance === "source")
      : [];
  const staleCount = sourceFacts.filter((f) => f.stale).length;

  return (
    <section aria-labelledby="case-title" className="dossier">
      <header className="dossier-head">
        <div>
          <h2 id="case-title">Dossier: {latest.address ?? listing.url}</h2>
          <p className="muted">
            Advertentie van {shortDate(latest.fetched_at)}
            {state.kind === "klaar" && state.data.built_from.profile_version !== null && (
              <> · Koperprofiel versie {state.data.built_from.profile_version}</>
            )}
            {staleCount > 0 && (
              <>
                {" "}
                · <span className="chip stale-chip">⏲ {staleCount} verouderd</span>
              </>
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
      {state.kind === "klaar" && (
        <KeyFigures
          askingPrice={latest.asking_price}
          affordability={state.data.affordability}
          metrics={state.data.metrics}
        />
      )}

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
          <Brondekking
            sources={state.data.sources}
            refetching={refetching}
            failed={refetchFailed}
            onRefetch={handleSourceRefetch}
          />
          <Betaalruimte affordability={state.data.affordability} rules={state.data.rules} />
          <FactGroup
            title="Kenmerken"
            id="kenmerken"
            facts={state.data.facts.filter((f): f is ListingFact => f.provenance === "listing")}
          />
          <SourceGroup
            title="Prijs en waarde"
            id="prijs-en-waarde"
            source="woz"
            facts={sourceFacts.filter((f) => f.source === "woz")}
            sources={state.data.sources}
          >
            {state.data.metrics.asking_vs_woz && (
              <ComputedRow
                label="Vraagprijs t.o.v. WOZ"
                value={`${percent.format(state.data.metrics.asking_vs_woz.percent)}% (${signedEuro(state.data.metrics.asking_vs_woz.difference)})`}
                note={`WOZ ${state.data.metrics.asking_vs_woz.woz_as_of.slice(0, 4)}`}
              />
            )}
          </SourceGroup>
          <SourceGroup
            title="Energie"
            id="energie"
            source="energielabel"
            facts={sourceFacts.filter((f) => f.source === "energielabel")}
            sources={state.data.sources}
          >
            {state.data.metrics.energy_label_check && (
              <ComputedRow
                label="Label advertentie gelijk aan register"
                value={
                  state.data.metrics.energy_label_check.matches
                    ? "Ja"
                    : `Nee: advertentie ${state.data.metrics.energy_label_check.listing}, register ${state.data.metrics.energy_label_check.register}`
                }
                note="vergelijking"
              />
            )}
          </SourceGroup>
        </>
      )}
    </section>
  );
}

function Brondekking(props: {
  sources: SourceStatus[];
  refetching: string | null;
  failed: boolean;
  onRefetch: (source: string) => void;
}) {
  const count = (status: SourceStatus["status"]) =>
    props.sources.filter((s) => s.status === status).length;
  return (
    <section aria-labelledby="brondekking-title" className="brondekking">
      <h3 id="brondekking-title">
        Brondekking: {props.sources.length} bronnen: {count("succeeded")} gelukt, {count("failed")}{" "}
        mislukt, {count("skipped")} overgeslagen
      </h3>
      <ul className="source-list">
        {props.sources.map((source) => {
          const copy = STATUS_COPY[source.status];
          return (
            <li key={source.source} className={`source-status ${source.status}`}>
              <span>
                <span aria-hidden="true">{copy.glyph} </span>
                {sourceLabel(source.source)}: {copy.word}
                {source.status !== "succeeded" && source.reason && REASON_COPY[source.reason] && (
                  <span className="muted"> ({REASON_COPY[source.reason]})</span>
                )}
                {source.attempted_at && (
                  <span className="muted"> · {shortDate(source.attempted_at)}</span>
                )}
              </span>
              <button
                type="button"
                className="small"
                disabled={props.refetching !== null}
                aria-label={`${sourceLabel(source.source)} opnieuw ophalen`}
                onClick={() => props.onRefetch(source.source)}
              >
                {props.refetching === source.source ? "Bezig…" : "Opnieuw ophalen"}
              </button>
            </li>
          );
        })}
      </ul>
      {props.failed && (
        <p role="alert" className="notice error">
          <span aria-hidden="true">! </span>Opnieuw ophalen mislukt. Probeer het later opnieuw.
        </p>
      )}
    </section>
  );
}

function KeyFigures({
  askingPrice,
  affordability,
  metrics,
}: {
  askingPrice: number | null;
  affordability: Affordability | null;
  metrics: Metrics;
}) {
  return (
    <dl className="figures key-figures" aria-label="Kerncijfers">
      <Figure label="Vraagprijs" value={askingPrice !== null ? euro.format(askingPrice) : "–"} />
      <Figure
        label="t.o.v. WOZ"
        value={metrics.asking_vs_woz ? `${percent.format(metrics.asking_vs_woz.percent)}%` : "–"}
      >
        {metrics.asking_vs_woz && "~ WOZ onofficieel"}
      </Figure>
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

function FactGroup({ title, id, facts }: { title: string; id: string; facts: ListingFact[] }) {
  return (
    <details open className="fact-group">
      <summary>
        <h3 id={`${id}-title`}>{title}</h3>
        <span className="muted">{facts.length} feiten</span>
      </summary>
      <ol className="facts">
        {facts.map((fact, index) => (
          <li key={fact.key} className="fact">
            <span className="vak-number">{index + 1}</span>
            <span className="fact-label">{FACT_LABELS[fact.key] ?? fact.key}</span>
            <span className="fact-value">{formatValue(fact)}</span>
            <span className="stamp" aria-label={`Bron: advertentie, opgehaald ${shortDate(fact.fetched_at)}`}>
              <span aria-hidden="true">■ ADV</span> Advertentie · {shortDate(fact.fetched_at)}
            </span>
          </li>
        ))}
      </ol>
    </details>
  );
}

function SourceGroup(props: {
  title: string;
  id: string;
  source: string;
  facts: SourceFact[];
  sources: SourceStatus[];
  children?: React.ReactNode;
}) {
  const status = props.sources.find((s) => s.source === props.source);
  const stale = props.facts.filter((f) => f.stale).length;
  return (
    <details open className="fact-group">
      <summary>
        <h3 id={`${props.id}-title`}>{props.title}</h3>
        <span className="muted">
          {props.facts.length} feiten{stale > 0 && ` · ${stale} verouderd`}
        </span>
      </summary>
      {props.facts.length === 0 && status && status.status !== "succeeded" && (
        <p className="empty">
          <span aria-hidden="true">{STATUS_COPY[status.status].glyph} </span>
          Bron {STATUS_COPY[status.status].word}, geen gegevens van {sourceLabel(props.source)}.
        </p>
      )}
      <ol className="facts">
        {props.facts.map((fact, index) => (
          <SourceFactRow key={`${fact.key}-${fact.as_of ?? index}`} fact={fact} number={index + 1} />
        ))}
        {props.children}
      </ol>
    </details>
  );
}

function SourceFactRow({ fact, number }: { fact: SourceFact; number: number }) {
  const official = fact.trust === "official";
  const fetched = shortDate(fact.fetched_at);
  const label = `Bron: ${sourceLabel(fact.source)}${official ? "" : ", onofficieel"}, opgehaald ${fetched}${fact.stale ? ", verouderd" : ""}`;
  return (
    <li className={`fact${fact.stale ? " stale" : ""}`}>
      <span className="vak-number">{number}</span>
      <span className="fact-label">{sourceFactLabel(fact)}</span>
      <span className="fact-value">
        {official ? "" : "~ "}
        {formatValue(fact)}
      </span>
      <span
        className={`stamp ${official ? "stamp-official" : "stamp-third-party"}`}
        aria-label={label}
        title={fact.ttl_days !== null ? `Verouderd na ${fact.ttl_days} dagen` : undefined}
      >
        <span aria-hidden="true">{official ? "◆ BRN" : "◇ 3DE"}</span> {sourceLabel(fact.source)}
        {!official && " · onofficieel"} ·{" "}
        {fact.stale ? (
          <>
            <s>{fetched}</s> <span aria-hidden="true">⏲</span> Verouderd
          </>
        ) : (
          fetched
        )}
      </span>
    </li>
  );
}

function ComputedRow(props: { label: string; value: string; note: string }) {
  return (
    <li className="fact">
      <span className="vak-number">=</span>
      <span className="fact-label">{props.label}</span>
      <span className="fact-value">{props.value}</span>
      <span className="stamp stamp-computed" aria-label={`Berekend: ${props.note}`}>
        <span aria-hidden="true">= BER</span> Berekend · {props.note}
      </span>
    </li>
  );
}
