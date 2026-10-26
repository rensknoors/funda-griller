import { CircleCheck, CircleMinus, CircleX, Clock, RefreshCw } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import {
  type Affordability,
  type Case,
  type Listing,
  type ListingFact,
  type Metrics,
  type SourceFact,
  type SourceStatus,
  type FindingFact,
  fetchCase,
  refetchSource,
} from "./api";
import { Documenten, VerkoperInformatie } from "./Documenten";
import { FACT_LABELS, ENVIRONMENT_FACTS, formatValue, isCommuteFact } from "./facts";
import { FotoWaarnemingen } from "./FotoWaarnemingen";
import { type Tone, euro, headroomTone, percentChange, priceTone, signedEuro, signedPercent } from "./format";
import { HardNoBanner, Signalen, signaalAnchor } from "./Signalen";
import { statusLabel } from "./ListingsTable";
import { TierMark } from "./TierMark";
import { plural } from "./plural";
import { tierOf } from "./comparison";
import { Vergelijkbaar, comparablesFigure, coverageNote } from "./Vergelijkbaar";
import { STAMP_LEGEND, Stamp } from "./Stamp";
import { Verbouwingskosten } from "./Verbouwingskosten";
import { type Neighbours, WoningHeader } from "./WoningHeader";

type LoadState = { kind: "laden" } | { kind: "fout" } | { kind: "klaar"; data: Case };

const dayMonth = new Intl.DateTimeFormat("nl-NL", { day: "numeric", month: "short" });
const shortDate = (iso: string) => dayMonth.format(new Date(iso));


const SOURCE_LABELS: Record<string, string> = {
  energielabel: "Energielabelregister",
  woz: "WOZ (prijshistorie)",
  flood_soil: "Overstroming en bodem",
  noise: "Geluid",
  comparables: "Vergelijkbare verkopen",
  commute: "Reistijd",
};
const sourceLabel = (source: string) => SOURCE_LABELS[source] ?? source;

const STATUS_COPY: Record<SourceStatus["status"], { icon: typeof CircleCheck; word: string }> = {
  succeeded: { icon: CircleCheck, word: "gelukt" },
  failed: { icon: CircleX, word: "mislukt" },
  skipped: { icon: CircleMinus, word: "overgeslagen" },
};
const REASON_COPY: Record<string, string> = {
  no_api_key: "geen API-sleutel ingesteld",
  no_address: "adres onvolledig",
  no_coordinates: "geen coördinaten",
  not_fetched: "nog niet opgehaald",
  no_destinations: "geen pendelbestemmingen in je Koperprofiel",
  destination_not_found: "adres van pendelbestemming niet gevonden",
  no_route: "geen route gevonden",
};


function sourceFactLabel(fact: SourceFact): string {
  if (fact.key === "woz_value") return `WOZ-waarde ${fact.as_of?.slice(0, 4) ?? ""}`.trim();
  if (fact.key === "energy_label") return "Energielabel (register)";
  if (isCommuteFact(fact.value)) return `Reistijd naar ${fact.value.destination}`;
  if (ENVIRONMENT_FACTS[fact.key]) return ENVIRONMENT_FACTS[fact.key].label;
  return FACT_LABELS[fact.key] ?? fact.key;
}

export function CaseView(props: {
  listing: Listing;
  neighbours: Neighbours;
  busy: boolean;
  onRefetch: (fundaId: string) => void;
  /** A Signaal to scroll to and expand once the Dossier has loaded (from an Oordeel chip). */
  focusFlagId?: string | null;
}) {
  const { listing, focusFlagId } = props;
  const [state, setState] = useState<LoadState>({ kind: "laden" });
  const [refetching, setRefetching] = useState<string | null>(null);
  const [refetchFailed, setRefetchFailed] = useState(false);
  const latest = listing.snapshots[0];
  const heading = useRef<HTMLHeadingElement>(null);
  const address = latest.address ?? listing.url;

  // A view switch moves focus and the tab title, so keyboard and screen-reader users land here.
  useEffect(() => {
    document.title = `Dossier: ${address} · Funda Griller`;
    heading.current?.focus();
  }, [address]);

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

  async function reloadCase() {
    setState({ kind: "klaar", data: await fetchCase(listing.funda_id) });
  }

  const loaded = state.kind === "klaar";
  useEffect(() => {
    if (loaded && focusFlagId) document.getElementById(signaalAnchor(focusFlagId))?.scrollIntoView();
  }, [loaded, focusFlagId]);

  const sourceFacts =
    state.kind === "klaar"
      ? state.data.facts.filter((f): f is SourceFact => f.provenance === "source")
      : [];
  const staleCount = sourceFacts.filter((f) => f.stale).length;

  return (
    <section aria-labelledby="dossier-title" className="dossier">
      <WoningHeader
        listing={listing}
        page="dossier"
        neighbours={props.neighbours}
        headingRef={heading}
        meta={
          <>
            <TierMark tier={tierOf(listing)} />
            {latest.status !== "available" && (
              <span className="chip status-chip">{statusLabel(latest.status, latest.raw_status)}</span>
            )}
            <span>
              Advertentie van {shortDate(latest.fetched_at)}
              {latest.entry === "manual" && <> · Handmatig ingevoerd</>}
              {state.kind === "klaar" && state.data.built_from.profile_version !== null && (
                <> · Koperprofiel versie {state.data.built_from.profile_version}</>
              )}
            </span>
            {staleCount > 0 && (
              <span className="chip stale-chip">
                <Clock size={13} aria-hidden="true" /> {staleCount} verouderd
              </span>
            )}
          </>
        }
        actions={
          <button type="button" disabled={props.busy} onClick={() => props.onRefetch(listing.funda_id)}>
            <RefreshCw size={15} aria-hidden="true" />
            Opnieuw ophalen
          </button>
        }
      />
      {state.kind === "klaar" && state.data.hard_no && (
        <HardNoBanner hardNo={state.data.hard_no} flags={state.data.flags} />
      )}
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
          Dossier laden mislukt. Sluit het dossier en open het
          opnieuw.
        </p>
      )}
      {state.kind === "klaar" && (
        <div className="dossier-body">
          <aside className="dossier-rail" aria-label="Overzicht">
            <OnThisPage commute={state.data.sources.some((s) => s.source === "commute")} />
            <Brondekking
              sources={state.data.sources}
              refetching={refetching}
              failed={refetchFailed}
              onRefetch={handleSourceRefetch}
            />
            <HerkomstLegend />
          </aside>
          <div className="dossier-main">
          <Signalen
            flags={state.data.flags}
            facts={state.data.facts}
            rulesVersion={state.data.built_from.flag_rules_version}
            focusFlagId={focusFlagId ?? null}
          />
          <Betaalruimte affordability={state.data.affordability} rules={state.data.rules} />
          <Verbouwingskosten estimate={state.data.renovation_estimate} facts={state.data.facts} />
          <FactGroup
            title="Kenmerken"
            id="kenmerken"
            facts={state.data.facts.filter((f): f is ListingFact => f.provenance === "listing")}
          />
          <SourceGroup
            title="Prijs en waarde"
            id="prijs-en-waarde"
            names={["woz"]}
            facts={sourceFacts.filter((f) => f.source === "woz")}
            sources={state.data.sources}
          >
            {state.data.metrics.asking_vs_woz && (
              <ComputedRow
                label="Vraagprijs t.o.v. WOZ"
                value={`${percentChange.format(state.data.metrics.asking_vs_woz.percent)}% (${signedEuro(state.data.metrics.asking_vs_woz.difference)})`}
                note={`WOZ ${state.data.metrics.asking_vs_woz.woz_as_of.slice(0, 4)}`}
              />
            )}
          </SourceGroup>
          <Vergelijkbaar
            metric={state.data.metrics.asking_vs_comparables}
            facts={sourceFacts.filter((f) => f.source === "comparables")}
            status={state.data.sources.find((s) => s.source === "comparables")}
            refetching={refetching}
            onFetch={() => handleSourceRefetch("comparables")}
          />
          <SourceGroup
            title="Energie"
            id="energie"
            names={["energielabel"]}
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
          <SourceGroup
            title="Omgeving"
            id="omgeving"
            names={["flood_soil", "noise"]}
            facts={sourceFacts.filter((f) => f.source === "flood_soil" || f.source === "noise")}
            sources={state.data.sources}
          />
          {state.data.sources.some((s) => s.source === "commute") && (
            <SourceGroup
              title="Reistijd"
              id="reistijd"
              names={["commute"]}
              facts={sourceFacts.filter((f) => f.source === "commute")}
              sources={state.data.sources}
            >
              {state.data.metrics.commute_coverage?.not_fetched.map((destination) => (
                <li key={destination}>
                  Reistijd naar {destination}: <strong>nog niet opgehaald</strong>{" "}
                  <span className="muted">
                    (nieuwe of gewijzigde pendelbestemming in je Koperprofiel; haal Reistijd opnieuw op)
                  </span>
                </li>
              ))}
              <li className="muted">
                Snelste van auto en fiets; openbaar vervoer niet meegerekend. Routes © openrouteservice.org
                by HeiGIT, kaartgegevens © OpenStreetMap-bijdragers; adressen via PDOK Locatieserver.
              </li>
            </SourceGroup>
          )}
          <VerkoperInformatie
            fundaId={listing.funda_id}
            findings={state.data.facts.filter((f): f is FindingFact => f.provenance === "finding")}
          />
          <FotoWaarnemingen
            data={state.data}
            fundaId={listing.funda_id}
            onCase={(data) => setState({ kind: "klaar", data })}
          />
          <Documenten fundaId={listing.funda_id} documents={state.data.documents} onChanged={reloadCase} />
          </div>
        </div>
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
    <section aria-labelledby="brondekking-title" className="rail-block brondekking">
      <h2 id="brondekking-title" className="rail-title">
        Brondekking
        <span className="rail-count">
          {props.sources.length} bronnen: {count("succeeded")} gelukt, {count("failed")} mislukt,{" "}
          {count("skipped")} overgeslagen
        </span>
      </h2>
      <ul className="source-list">
        {props.sources.map((source) => {
          const copy = STATUS_COPY[source.status];
          const Icon = copy.icon;
          return (
            <li key={source.source} className={`source-status ${source.status}`}>
              <Icon size={16} aria-hidden="true" className="source-icon" />
              <span className="source-text">
                <span className="source-name">
                  {sourceLabel(source.source)}: {copy.word}
                </span>
                {source.status !== "succeeded" && source.reason && REASON_COPY[source.reason] && (
                  <span className="muted"> ({REASON_COPY[source.reason]})</span>
                )}
                {source.attempted_at && <span className="muted"> · {shortDate(source.attempted_at)}</span>}
              </span>
              <button
                type="button"
                className="icon-button"
                disabled={props.refetching !== null}
                aria-label={`${sourceLabel(source.source)} opnieuw ophalen`}
                title="Opnieuw ophalen"
                onClick={() => props.onRefetch(source.source)}
              >
                <RefreshCw size={15} aria-hidden="true" className={props.refetching === source.source ? "spinning" : undefined} />
              </button>
            </li>
          );
        })}
      </ul>
      {props.failed && (
        <p role="alert" className="notice error">
          Opnieuw ophalen mislukt. Probeer het later opnieuw.
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
        tone={priceTone(metrics.asking_vs_woz?.percent)}
        value={metrics.asking_vs_woz ? signedPercent(metrics.asking_vs_woz.percent) : "–"}
      >
        {metrics.asking_vs_woz && "~ WOZ onofficieel"}
      </Figure>
      <Figure
        label="t.o.v. vergelijkbaar"
        tone={priceTone(metrics.asking_vs_comparables.percent)}
        value={comparablesFigure(metrics.asking_vs_comparables)}
      >
        {coverageNote(metrics.asking_vs_comparables)}
      </Figure>
      <Figure
        label="Ruimte boven vraag"
        tone={headroomTone(affordability?.headroom)}
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
      <h2 id="betaalruimte-title">Betaalruimte</h2>
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
              "Let op: de benodigde hypotheek is hoger dan de maximale hypotheek"}
          </Figure>
          <Figure
            label="Ruimte boven vraag"
            tone={headroomTone(affordability.headroom)}
            value={affordability.headroom !== null ? signedEuro(affordability.headroom) : "–"}
          >
            {affordability.renovation_direct > 0 &&
              `na aftrek van ${euro.format(affordability.renovation_direct)} Direct nodig onderhoud`}
          </Figure>
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

/** What each herkomst label means, beside the facts so the labels are learnable. */
function HerkomstLegend() {
  return (
    <section aria-labelledby="herkomst-title" className="rail-block">
      <h2 id="herkomst-title" className="rail-title">Herkomst</h2>
      <dl className="herkomst-legend">
        {STAMP_LEGEND.map(([kind, word, meaning]) => (
          <div key={kind}>
            <dt>
              <Stamp kind={kind}>{word}</Stamp>
            </dt>
            <dd>{meaning}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

const SECTIONS: [id: string, title: string][] = [
  ["signalen-title", "Signalen"],
  ["betaalruimte-title", "Betaalruimte"],
  ["verbouwingskosten-title", "Verbouwingskosten"],
  ["kenmerken-title", "Kenmerken"],
  ["prijs-en-waarde-title", "Prijs en waarde"],
  ["vergelijkbaar-title", "Vergelijkbare woningen"],
  ["energie-title", "Energie"],
  ["omgeving-title", "Omgeving"],
  ["reistijd-title", "Reistijd"],
  ["verkoper-informatie-title", "Verkoper-informatie"],
  ["foto-waarnemingen-title", "Foto-waarnemingen"],
  ["documenten-title", "Documenten"],
];

/** The Dossier's sections as jump links; the Dossier is long and every section is a reason to come back. */
function OnThisPage({ commute }: { commute: boolean }) {
  return (
    <nav aria-label="Op deze pagina" className="rail-block on-this-page">
      <h2 className="rail-title">Op deze pagina</h2>
      <ol>
        {SECTIONS.filter(([id]) => commute || id !== "reistijd-title").map(([id, title]) => (
          <li key={id}>
            <a href={`#${id}`}>{title}</a>
          </li>
        ))}
      </ol>
    </nav>
  );
}

function Figure(props: { label: string; value: string; tone?: Tone; children?: React.ReactNode }) {
  return (
    <div className="figure">
      <dt>{props.label}</dt>
      <dd className={props.tone ? `num tone-${props.tone}` : "num"}>{props.value}</dd>
      {props.children && <dd className="muted note">{props.children}</dd>}
    </div>
  );
}

function FactGroup({ title, id, facts }: { title: string; id: string; facts: ListingFact[] }) {
  return (
    <details open className="fact-group">
      <summary>
        <h2 id={`${id}-title`}>{title}</h2>
        <span className="muted">{plural(facts.length, "feit", "feiten")}</span>
      </summary>
      <ol className="facts">
        {facts.map((fact, index) => (
          <li key={fact.key} id={`vak-${index + 1}`} className="fact">
            <span className="vak-number">{index + 1}</span>
            <span className="fact-label">{FACT_LABELS[fact.key] ?? fact.key}</span>
            <span className="fact-value">{formatValue(fact)}</span>
            <Stamp kind="listing" label={`Bron: advertentie, opgehaald ${shortDate(fact.fetched_at)}`}>
              Advertentie · {shortDate(fact.fetched_at)}
            </Stamp>
          </li>
        ))}
      </ol>
    </details>
  );
}

function SourceGroup(props: {
  title: string;
  id: string;
  names: string[];
  facts: SourceFact[];
  sources: SourceStatus[];
  children?: React.ReactNode;
}) {
  // A Source without facts says so in place, never silently absent.
  const empty = props.names
    .map((name) => props.sources.find((s) => s.source === name))
    .filter(
      (status): status is SourceStatus =>
        status !== undefined &&
        status.status !== "succeeded" &&
        !props.facts.some((f) => f.source === status.source),
    );
  const stale = props.facts.filter((f) => f.stale).length;
  return (
    <details open className="fact-group">
      <summary>
        <h2 id={`${props.id}-title`}>{props.title}</h2>
        <span className="muted">
          {plural(props.facts.length, "feit", "feiten")}{stale > 0 && ` · ${stale} verouderd`}
        </span>
      </summary>
      {empty.map((status) => (
        <p key={status.source} className="empty">
          Bron {STATUS_COPY[status.status].word}, geen gegevens van {sourceLabel(status.source)}.
        </p>
      ))}
      <ol className="facts">
        {props.facts.map((fact, index) => (
          <SourceFactRow key={`${fact.key}-${fact.as_of ?? index}`} fact={fact} />
        ))}
        {props.children}
      </ol>
    </details>
  );
}

function SourceFactRow({ fact }: { fact: SourceFact }) {
  const official = fact.trust === "official";
  const fetched = shortDate(fact.fetched_at);
  const label = `Bron: ${sourceLabel(fact.source)}${official ? "" : ", onofficieel"}, opgehaald ${fetched}${fact.stale ? ", verouderd" : ""}`;
  return (
    <li className={`fact${fact.stale ? " stale" : ""}`}>
      <span className="vak-number" />
      <span className="fact-label">{sourceFactLabel(fact)}</span>
      <span className="fact-value">
        {official ? "" : "~ "}
        {formatValue(fact)}
      </span>
      <Stamp
        kind={official ? "official" : "third-party"}
        label={label}
        title={fact.ttl_days !== null ? `Verouderd na ${fact.ttl_days} dagen` : undefined}
      >
        {sourceLabel(fact.source)}
        {!official && " · onofficieel"} ·{" "}
        {fact.stale ? (
          <>
            <s>{fetched}</s> <Clock size={13} aria-hidden="true" className="inline-icon" /> Verouderd
          </>
        ) : (
          fetched
        )}
      </Stamp>
    </li>
  );
}


function ComputedRow(props: { label: string; value: string; note: string }) {
  return (
    <li className="fact">
      <span className="vak-number">=</span>
      <span className="fact-label">{props.label}</span>
      <span className="fact-value">{props.value}</span>
      <Stamp kind="computed" label={`Berekend: ${props.note}`}>
        Berekend · {props.note}
      </Stamp>
    </li>
  );
}
