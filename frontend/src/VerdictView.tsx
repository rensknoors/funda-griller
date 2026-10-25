import { useEffect, useRef, useState } from "react";

import {
  type BidAdvice,
  type FlagClass,
  type Listing,
  type Verdict,
  type VerdictError,
  type VerdictInput,
  type VerdictState,
  type WalkAwayDerivation,
  fetchVerdicts,
  isVerdictError,
  runVerdict,
} from "./api";
import { TIER_LABEL } from "./comparison";
import { euro } from "./format";
import { statusLabel } from "./ListingsTable";
import { TierMark } from "./TierMark";
import { coverageNote } from "./Vergelijkbaar";

type LoadState = { kind: "laden" } | { kind: "fout" } | { kind: "klaar"; data: VerdictState };

const dateTime = new Intl.DateTimeFormat("nl-NL", { dateStyle: "medium", timeStyle: "short" });

const FLAG_GLYPHS: Record<FlagClass, string> = { pro: "+", con: "−", risk: "!" };

const CHANGED_COPY: Record<VerdictInput, string> = {
  case: "het dossier",
  buyer_profile: "je koperprofiel",
  rules: "de regels",
  model: "het model",
};

const ERROR_COPY: Record<VerdictError["kind"], string> = {
  no_buyer_profile: "Vul eerst je koperprofiel in; zonder profiel is er geen oordeel.",
  invalid_verdict: "Het model gaf een ongeldig antwoord. Het is niet bewaard.",
  llm_unavailable: "Het model is niet bereikbaar. Probeer het later opnieuw.",
  unknown: "Oordeel opvragen mislukt. Probeer het opnieuw.",
};

export function VerdictView(props: {
  listing: Listing;
  onBackToCase: () => void;
  onShowFlag: (flagId: string) => void;
}) {
  const { listing } = props;
  const [state, setState] = useState<LoadState>({ kind: "laden" });
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<VerdictError | null>(null);
  const snapshot = listing.snapshots[0];
  const address = snapshot.address ?? listing.url;
  const heading = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    document.title = `Oordeel: ${address} · Funda Griller`;
    heading.current?.focus();
  }, [address]);

  useEffect(() => {
    let current = true;
    fetchVerdicts(listing.funda_id)
      .then((data) => current && setState({ kind: "klaar", data }))
      .catch(() => current && setState({ kind: "fout" }));
    return () => {
      current = false;
    };
  }, [listing.funda_id]);

  async function handleRun() {
    setRunning(true);
    setRunError(null);
    const result = await runVerdict(listing.funda_id);
    if (isVerdictError(result)) {
      setRunError(result);
    } else {
      try {
        setState({ kind: "klaar", data: await fetchVerdicts(listing.funda_id) });
      } catch {
        setState({ kind: "fout" });
      }
    }
    setRunning(false);
  }

  const data = state.kind === "klaar" ? state.data : null;
  const latest = data?.verdicts[0];

  return (
    <section aria-labelledby="verdict-title" className="oordeel">
      <header className="dossier-head">
        <h2 id="verdict-title" ref={heading} tabIndex={-1}>
          Oordeel: {address}
        </h2>
        <div className="row">
          <button type="button" onClick={props.onBackToCase}>
            Terug naar dossier
          </button>
        </div>
      </header>

      {snapshot.status !== "available" && (
        <div role="status" className="status-banner">
          <span className="chip status-chip">{statusLabel(snapshot.status, snapshot.raw_status)}</span>{" "}
          <strong>
            {snapshot.status === "negotiations"
              ? "Deze woning is onder bod. Controleer bij de makelaar of er nog geboden kan worden."
              : "Deze woning is verkocht. Een biedadvies is niet meer van toepassing."}
          </strong>
        </div>
      )}
      {state.kind === "laden" && <TierSkeleton status="Oordeel laden" />}
      {state.kind === "fout" && (
        <p role="alert" className="notice error">
          <span aria-hidden="true">! </span>Oordeel laden mislukt. Ga terug naar het dossier en
          open het oordeel opnieuw.
        </p>
      )}
      {data && !latest && !running && (
        <div className="empty-vak">
          <p>
            <strong>Nog geen oordeel.</strong> Een oordeel leest het dossier van deze woning samen met
            je koperprofiel en geeft een van vier uitkomsten, met biedadvies. Een deal-breaker uit je
            profiel geeft direct een harde afwijzing, zonder model.
          </p>
          <button type="button" className="primary" onClick={handleRun}>
            Oordeel opvragen
          </button>
        </div>
      )}
      {running && <TierSkeleton status="Model leest dossier…" />}
      {runError && (
        <p role="alert" className="notice error">
          <span aria-hidden="true">! </span>
          {ERROR_COPY[runError.kind]}{" "}
          {runError.kind === "invalid_verdict" && (
            <span className="muted">({runError.problems.join(", ")})</span>
          )}{" "}
          {runError.kind !== "no_buyer_profile" && (
            <button type="button" onClick={handleRun} disabled={running}>
              Opnieuw proberen
            </button>
          )}
          {latest && <> Het vorige oordeel blijft hieronder staan.</>}
        </p>
      )}

      {data && latest && !running && (
        <>
          {data.out_of_date && (
            <div role="status" className="achterhaald-banner">
              <span className="chip stale-chip">Achterhaald</span>{" "}
              <strong>Dit oordeel is gebaseerd op een oudere versie</strong> van{" "}
              {data.changed.map((input) => CHANGED_COPY[input]).join(" en ")}.{" "}
              <button type="button" className="primary" onClick={handleRun}>
                Oordeel opnieuw draaien
              </button>
            </div>
          )}
          <TierBlock verdict={latest} outOfDate={data.out_of_date} />
          <Redenering verdict={latest} onShowFlag={props.onShowFlag} />
          {latest.bid_advice && <Biedadvies advice={latest.bid_advice} rulesYear={latest.built_from.rules_year} />}
          <VersieStempel verdicts={data.verdicts} />
          {!data.out_of_date && (
            <p className="row">
              <button type="button" onClick={handleRun}>
                Oordeel opnieuw draaien
              </button>
            </p>
          )}
        </>
      )}
    </section>
  );
}

function TierSkeleton({ status }: { status: string }) {
  return (
    <div className="skeleton tier-skeleton" aria-busy="true">
      <p role="status" className="muted">
        {status}
      </p>
      <div className="skeleton-row" />
      <div className="skeleton-row" />
    </div>
  );
}

function TierBlock({ verdict, outOfDate }: { verdict: Verdict; outOfDate: boolean }) {
  return (
    <section
      aria-labelledby="tier-title"
      className={`tier-block tier-block-${verdict.tier}${outOfDate ? " out-of-date" : ""}`}
    >
      <h3 id="tier-title">Oordeel</h3>
      <TierMark tier={verdict.tier} size="large" />
      {verdict.tier === "hard_no" && verdict.deal_breaker ? (
        <>
          <p className="tier-summary">
            Deal-breaker: <strong>{verdict.deal_breaker}</strong>
          </p>
          {verdict.deterministic && (
            <p className="muted">Deterministisch toegepast, geen model gebruikt.</p>
          )}
        </>
      ) : (
        verdict.summary && <p className="tier-summary">{verdict.summary}</p>
      )}
    </section>
  );
}

function Redenering({ verdict, onShowFlag }: { verdict: Verdict; onShowFlag: (flagId: string) => void }) {
  return (
    <section aria-labelledby="redenering-title">
      <h3 id="redenering-title">Redenering</h3>
      <p className="prose">{verdict.reasoning}</p>
      {verdict.cited_flags.length > 0 && (
        <p className="signaal-chips">
          <span className="muted">Steunt op: </span>
          {verdict.cited_flags.map((flag) => (
            <button
              key={flag.id}
              type="button"
              className={`signaal-chip flag-${flag.class}`}
              onClick={() => onShowFlag(flag.id)}
            >
              <span className="flag-glyph" aria-hidden="true">
                {FLAG_GLYPHS[flag.class]}
              </span>{" "}
              {flag.title}
            </button>
          ))}
        </p>
      )}
    </section>
  );
}

function Biedadvies({ advice, rulesYear }: { advice: BidAdvice; rulesYear: number }) {
  const headroom = advice.asking_price !== null ? advice.affordable_maximum - advice.asking_price : null;
  return (
    <section aria-labelledby="biedadvies-title">
      <h3 id="biedadvies-title">Biedadvies</h3>
      <div className="bid-vakken">
        <div className="figure">
          <p className="vak-label">Openingsbod</p>
          <p className="bid-amount num">{euro.format(advice.opening_bid)}</p>
        </div>
        <div className="figure">
          <p className="vak-label">Maximumbod</p>
          <p className="bid-amount num">{euro.format(advice.walk_away_maximum)}</p>
          {advice.derivation?.weakly_grounded && (
            <p className="weak-grounding">{weakGroundingNote(advice.derivation)}</p>
          )}
          <details>
            <summary>Hoe berekend</summary>
            <ul className="evidence">
              <li>
                Betaalruimte: tot {euro.format(advice.affordable_maximum)}{" "}
                <span className="muted">(koperprofiel en regels {rulesYear}, incl. kosten koper)</span>
              </li>
              <li>
                Vergelijkbare woningen:{" "}
                {advice.comparables ? (
                  <>
                    {advice.comparables.comparables_value !== null &&
                      `waarde ${euro.format(advice.comparables.comparables_value)} `}
                    <span className="muted">({coverageNote(advice.comparables)})</span>
                  </>
                ) : (
                  <span className="muted">niet meegenomen in dit oordeel</span>
                )}
              </li>
              {advice.derivation ? (
                <>
                  {basisLine(advice, advice.derivation) && <li>{basisLine(advice, advice.derivation)}</li>}
                  <li>{bindingLine(advice, advice.derivation)}</li>
                </>
              ) : (
                <li>
                  <ModelBindingLimit advice={advice} />
                </li>
              )}
            </ul>
          </details>
        </div>
        <div className="figure">
          <p className="vak-label">Voorwaarden</p>
          {advice.conditions.length === 0 ? (
            <p className="muted">Geen voorwaarden geadviseerd.</p>
          ) : (
            <ul className="conditions">
              {advice.conditions.map((condition) => (
                <li key={condition}>
                  <span aria-hidden="true">☐ </span>
                  {condition}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <dl className="figures bid-context">
        <BidFigure label="Maandlasten bij vraagprijs" amount={advice.monthly_cost_at_asking_price} perMonth />
        <BidFigure label="Maandlasten bij Maximumbod" amount={advice.monthly_cost_at_walk_away_maximum} perMonth />
        <div className="figure">
          <dt>Ruimte boven vraag</dt>
          <dd className="num">
            {headroom === null ? "–" : `${headroom >= 0 ? "▲ +" : "▼ "}${euro.format(headroom)}`}
          </dd>
        </div>
      </dl>
      <p className="muted rules-year">Regels {rulesYear}</p>
    </section>
  );
}

const percent = (share: number) => `${(Math.round(share * 1000) / 10).toLocaleString("nl-NL")}%`;

/** Said next to the Maximumbod, not tucked into "Hoe berekend": without comparables it is a guess. */
function weakGroundingNote(derivation: WalkAwayDerivation): string {
  return derivation.basis === "asking_price"
    ? "Zwak onderbouwd: te weinig vergelijkbare woningen, dus gebaseerd op de vraagprijs in plaats van op wat de woning waard is."
    : "Zwak onderbouwd: geen vergelijkbare woningen en geen vraagprijs, dus alleen begrensd door je betaalruimte.";
}

/** "Vraagprijs € 595.000 + 5%: € 624.750": the basis and its margin. */
function basisLine(advice: BidAdvice, derivation: WalkAwayDerivation): string | null {
  if (derivation.basis_maximum === null || derivation.margin === null) return null;
  const value = derivation.basis === "comparables" ? advice.comparables?.comparables_value : advice.asking_price;
  if (value == null) return null;
  const label = derivation.basis === "comparables" ? "Vergelijkbare woningen" : "Vraagprijs";
  return `${label} ${euro.format(value)} + ${percent(derivation.margin)}: ${euro.format(derivation.basis_maximum)}`;
}

/** Which of the two set the Maximumbod: its basis plus margin, or the betaalruimte. */
function bindingLine(advice: BidAdvice, derivation: WalkAwayDerivation): string {
  const maximum = euro.format(advice.walk_away_maximum);
  if (derivation.basis === "affordability") return `Maximumbod: de betaalruimte, ${maximum}.`;
  const basis = derivation.basis === "comparables" ? "vergelijkbare woningen" : "vraagprijs";
  return derivation.binding === "basis"
    ? `Maximumbod: de ${basis} plus marge, ${maximum}, onder de betaalruimte.`
    : `Maximumbod: de betaalruimte, ${maximum}, lager dan de ${basis} plus marge.`;
}

/** For older Verdicts whose model proposed the Maximumbod: names the lowest limit it stayed under. */
function ModelBindingLimit({ advice }: { advice: BidAdvice }) {
  const comparables = advice.comparables?.maximum ?? null;
  const byComparables = comparables !== null && comparables < advice.affordable_maximum;
  const limit = byComparables ? comparables : advice.affordable_maximum;
  const below = limit - advice.walk_away_maximum;
  return (
    <>
      Laagste grens: {byComparables ? "vergelijkbare woningen" : "betaalruimte"}, {euro.format(limit)}.{" "}
      {below > 0
        ? `Het Maximumbod blijft daar ${euro.format(below)} onder.`
        : "Het Maximumbod is gelijk aan die grens."}
    </>
  );
}

function BidFigure({ label, amount, perMonth }: { label: string; amount: number | null; perMonth?: boolean }) {
  return (
    <div className="figure">
      <dt>{label}</dt>
      <dd className="num">{amount === null ? "–" : `${euro.format(amount)}${perMonth ? " p/m" : ""}`}</dd>
    </div>
  );
}

function VersieStempel({ verdicts }: { verdicts: Verdict[] }) {
  const [latest, ...older] = verdicts;
  return (
    <section aria-labelledby="versie-title">
      <h3 id="versie-title">Versie</h3>
      <p>
        <VersionLine verdict={latest} />
      </p>
      {older.length > 0 && (
        <details>
          <summary>Eerdere oordelen ({older.length})</summary>
          <ol className="verdict-history">
            {older.map((verdict, index) => (
              <li key={verdict.id}>
                <VersionLine verdict={verdict} />
                <br />
                <span className="muted">{describeChange(verdict, verdicts[index])}</span>
              </li>
            ))}
          </ol>
        </details>
      )}
    </section>
  );
}

function VersionLine({ verdict }: { verdict: Verdict }) {
  const from = verdict.built_from;
  return (
    <>
      <strong>Versie {verdict.version}</strong> · {dateTime.format(new Date(verdict.created_at))} ·{" "}
      {TIER_LABEL[verdict.tier]} · Dossier momentopname {from.snapshot_id} · Koperprofiel versie{" "}
      {from.profile_version ?? "–"} · Regelset {from.flag_rules_version}, regels {from.rules_year} ·{" "}
      {from.model ? `Model ${from.model}` : "Geen model"}
    </>
  );
}

/** "Was Overwegen, nu Zeker kopen: koperprofiel 1 → 2, Maximumbod +€ 10.000". */
function describeChange(older: Verdict, newer: Verdict): string {
  const parts: string[] = [];
  if (older.built_from.profile_version !== newer.built_from.profile_version) {
    parts.push(`koperprofiel ${older.built_from.profile_version} → ${newer.built_from.profile_version}`);
  }
  if (older.built_from.snapshot_id !== newer.built_from.snapshot_id) parts.push("nieuwe momentopname");
  if (older.built_from.model !== newer.built_from.model) parts.push("ander model");
  const before = older.bid_advice?.walk_away_maximum;
  const after = newer.bid_advice?.walk_away_maximum;
  if (before !== undefined && after !== undefined && before !== after) {
    parts.push(`Maximumbod ${after > before ? "+" : "−"}${euro.format(Math.abs(after - before))}`);
  }
  const tiers =
    older.tier === newer.tier
      ? `Bleef ${TIER_LABEL[older.tier]}`
      : `Was ${TIER_LABEL[older.tier]}, daarna ${TIER_LABEL[newer.tier]}`;
  return parts.length > 0 ? `${tiers}: ${parts.join(", ")}` : tiers;
}
