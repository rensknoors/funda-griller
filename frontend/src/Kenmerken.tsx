import { Dialog } from "@base-ui/react/dialog";
import { Pencil } from "lucide-react";
import { useState } from "react";

import {
  type Case,
  type CaseFact,
  type CorrectableKey,
  type CorrectionError,
  type CorrectionFact,
  type ListingFact,
  CORRECTABLE_KEYS,
  correctFact,
  keepCorrection,
  removeCorrection,
} from "./api";
import { FACT_LABELS, factText, formatScalar, formatValue, isKenmerk } from "./facts";
import { plural } from "./plural";
import { Stamp } from "./Stamp";
import { Vak } from "./Vak";

const dayMonth = new Intl.DateTimeFormat("nl-NL", { day: "numeric", month: "short" });
const shortDate = (iso: string) => dayMonth.format(new Date(iso));

const ENERGY_LABELS = ["A++++", "A+++", "A++", "A+", "A", "B", "C", "D", "E", "F", "G"];
// funda's soorten woning that app/house_type.py recognises; a Correctie names one of them.
const HOUSE_TYPES = [
  "Eengezinswoning, tussenwoning",
  "Eengezinswoning, hoekwoning",
  "Eengezinswoning, eindwoning",
  "Eengezinswoning, 2-onder-1-kapwoning",
  "Eengezinswoning, geschakelde woning",
  "Eengezinswoning, vrijstaande woning",
  "Herenhuis",
  "Villa",
  "Bungalow",
  "Woonboerderij",
  "Appartement",
  "Bovenwoning",
  "Benedenwoning",
  "Maisonnette",
  "Portiekflat",
  "Galerijflat",
  "Penthouse",
];
const NUMBER_KEYS = new Set<CorrectableKey>(["living_area", "plot_area", "rooms", "bedrooms", "construction_year"]);

const isCorrectable = (key: string): key is CorrectableKey => (CORRECTABLE_KEYS as readonly string[]).includes(key);
const label = (key: string) => FACT_LABELS[key] ?? key;
/** Where a corrected fact's original came from: the register's energielabel or the advertentie. */
const originLabel = (provenance: "listing" | "source") => (provenance === "source" ? "Register" : "Advertentie");

type Row =
  | { kind: "listing"; fact: ListingFact }
  | { kind: "correction"; fact: CorrectionFact }
  | { kind: "missing"; key: CorrectableKey };

/**
 * The Listing's facts, numbered as vakken. Every fact the Case computes with has a pencil that
 * opens a Correctie, also when the advertentie leaves it out; a corrected fact shows its original
 * and why it was corrected.
 */
export function Kenmerken(props: { fundaId: string; facts: CaseFact[]; onCase: (data: Case) => void }) {
  const kenmerken = props.facts.filter(isKenmerk);
  const missing = CORRECTABLE_KEYS.filter((key) => !kenmerken.some((fact) => fact.key === key));
  const rows: Row[] = [
    ...kenmerken.map((fact): Row => (fact.provenance === "correction" ? { kind: "correction", fact } : { kind: "listing", fact })),
    ...missing.map((key): Row => ({ kind: "missing", key })),
  ];
  const [editing, setEditing] = useState<CorrectableKey | null>(null);
  const editingRow = rows.find((row) => (row.kind === "missing" ? row.key : row.fact.key) === editing);

  return (
    <details open className="fact-group">
      <summary>
        <h2 id="kenmerken-title">Kenmerken</h2>
        <span className="muted">{plural(kenmerken.length, "feit", "feiten")}</span>
      </summary>
      <ol className="facts">
        {rows.map((row, index) => {
          const key = row.kind === "missing" ? row.key : row.fact.key;
          const vak = row.kind === "missing" ? null : index + 1;
          const pencil = isCorrectable(key) && (
            <button
              type="button"
              className="icon-button correct-button"
              aria-label={`${label(key)} corrigeren`}
              title="Corrigeren"
              onClick={() => setEditing(key)}
            >
              <Pencil size={14} aria-hidden="true" />
            </button>
          );
          return (
            <li key={key} id={vak ? `vak-${vak}` : undefined} className={`fact${row.kind === "correction" ? " corrected" : ""}`}>
              <span className="vak-number">{vak}</span>
              <span className="fact-label">{label(key)}</span>
              {row.kind === "missing" && (
                <>
                  <span className="fact-value">
                    <span className="muted">onbekend</span>
                    {pencil}
                  </span>
                  <span className="muted not-stated">niet in de advertentie</span>
                </>
              )}
              {row.kind === "listing" && (
                <>
                  <span className="fact-value">
                    {formatValue(row.fact)}
                    {pencil}
                  </span>
                  <Stamp kind="listing" label={`Bron: advertentie, opgehaald ${shortDate(row.fact.fetched_at)}`}>
                    Advertentie · {shortDate(row.fact.fetched_at)}
                  </Stamp>
                </>
              )}
              {row.kind === "correction" && (
                <>
                  <CorrectedValue fact={row.fact} pencil={pencil} fundaId={props.fundaId} onCase={props.onCase} />
                  <Stamp kind="correction" label={`Correctie: eigen waarde, ingevoerd ${shortDate(row.fact.corrected_at)}`}>
                    Correctie · {shortDate(row.fact.corrected_at)}
                  </Stamp>
                </>
              )}
            </li>
          );
        })}
      </ol>
      {editing && editingRow && (
        <CorrectieDialog
          key={editing}
          fundaId={props.fundaId}
          factKey={editing}
          row={editingRow}
          onClose={() => setEditing(null)}
          onCase={(data) => {
            setEditing(null);
            props.onCase(data);
          }}
        />
      )}
    </details>
  );
}

/** The household's value marked gecorrigeerd, the value it replaces struck through with its
 * herkomst, the Toelichting, and a notice when the advertentie has moved since. */
function CorrectedValue(props: {
  fact: CorrectionFact;
  pencil: React.ReactNode;
  fundaId: string;
  onCase: (data: Case) => void;
}) {
  const { fact } = props;
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  async function act(run: () => Promise<Case>) {
    setBusy(true);
    setFailed(false);
    try {
      props.onCase(await run());
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <span className="fact-value correction">
      <span className="correction-head">
        <span>{formatValue(fact)}</span> <span className="chip correction-chip">gecorrigeerd</span>
        {props.pencil}
      </span>
      <span className="correction-original">
        {fact.original.provenance === null ? (
          <s>onbekend</s>
        ) : (
          <>
            <s>{formatScalar(fact.key, fact.original.value)}</s>{" "}
            <Stamp kind={fact.original.provenance === "source" ? "official" : "listing"}>
              {originLabel(fact.original.provenance)}
            </Stamp>
          </>
        )}
      </span>
      <span className="correction-explanation">Toelichting: {fact.explanation}</span>
      {fact.listing_changed && (
        <span role="status" className="correction-changed">
          <span>
            {fact.original.provenance === "listing"
              ? `De advertentie noemt nu ${factText(fact.key, fact.original.value)}.`
              : "De advertentie noemt dit niet meer."}{" "}
            Klopt je correctie nog?
          </span>
          <span className="correction-actions">
            <button type="button" className="small" disabled={busy} onClick={() => act(() => keepCorrection(props.fundaId, fact.key))}>
              Correctie behouden
            </button>
            <button
              type="button"
              className="small destructive"
              disabled={busy}
              onClick={() => act(() => removeCorrection(props.fundaId, fact.key))}
            >
              Correctie verwijderen
            </button>
          </span>
          {failed && <span className="vak-error">Dat lukte niet. Probeer het opnieuw.</span>}
        </span>
      )}
    </span>
  );
}

const ERROR_COPY: Record<CorrectionError, string> = {
  invalid_value: "Deze waarde kan niet.",
  explanation_required: "Schrijf erbij waar de waarde vandaan komt.",
  unavailable: "Opslaan lukte niet. Probeer het opnieuw.",
};

function invalidValueCopy(key: CorrectableKey): string {
  if (key === "construction_year") return "Vul een bouwjaar in, bijvoorbeeld 1931.";
  if (NUMBER_KEYS.has(key)) return "Vul een heel getal boven 0 in.";
  return "Kies of vul een waarde in.";
}

/** The small dialog behind a pencil: the value, the Toelichting, and removal of a Correctie. */
function CorrectieDialog(props: {
  fundaId: string;
  factKey: CorrectableKey;
  row: Row;
  onClose: () => void;
  onCase: (data: Case) => void;
}) {
  const { factKey: key, row } = props;
  const correction = row.kind === "correction" ? row.fact : null;
  const current = row.kind === "missing" ? "" : String(row.fact.value);
  const [value, setValue] = useState(current);
  const [explanation, setExplanation] = useState(correction?.explanation ?? "");
  const [error, setError] = useState<{ field: "value" | "explanation" | "form"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const original = correction
    ? correction.original
    : row.kind === "listing"
      ? { value: row.fact.value, provenance: "listing" as const }
      : { value: null, provenance: null };
  const originalText =
    original.provenance === null
      ? "De advertentie noemt dit niet."
      : `${originLabel(original.provenance)}: ${factText(key, original.value)}.`;

  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (!explanation.trim()) {
      setError({ field: "explanation", text: ERROR_COPY.explanation_required });
      return;
    }
    const number = /^\s*\d+\s*$/.test(value) ? Number(value) : null;
    if (NUMBER_KEYS.has(key) && (number === null || number <= 0)) {
      setError({ field: "value", text: invalidValueCopy(key) });
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await correctFact(props.fundaId, key, number ?? value.trim(), explanation.trim());
      if (!("error" in result)) return props.onCase(result);
      if (result.error === "invalid_value") setError({ field: "value", text: invalidValueCopy(key) });
      else if (result.error === "explanation_required") setError({ field: "explanation", text: ERROR_COPY.explanation_required });
      else setError({ field: "form", text: ERROR_COPY.unavailable });
    } catch {
      setError({ field: "form", text: ERROR_COPY.unavailable });
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    setError(null);
    try {
      props.onCase(await removeCorrection(props.fundaId, key));
    } catch {
      setError({ field: "form", text: "Verwijderen lukte niet. Probeer het opnieuw." });
      setBusy(false);
    }
  }

  return (
    <Dialog.Root open onOpenChange={(open) => !open && props.onClose()}>
      <Dialog.Portal>
        <Dialog.Backdrop className="dialog-backdrop" />
        <Dialog.Popup className="dialog correctie-dialog">
          <Dialog.Title>{label(key)} corrigeren</Dialog.Title>
          <Dialog.Description>
            {originalText} Je correctie telt in elke berekening mee; de oorspronkelijke waarde blijft zichtbaar.
          </Dialog.Description>
          <form onSubmit={save} noValidate>
            <Vak label={label(key)} error={error?.field === "value" ? error.text : undefined}>
              {(input) =>
                key === "energy_label" || key === "house_type" ? (
                  <select {...input} value={value} onChange={(e) => setValue(e.target.value)}>
                    <option value="">Kies…</option>
                    {(key === "energy_label" ? ENERGY_LABELS : HOUSE_TYPES).map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                    {value && !(key === "energy_label" ? ENERGY_LABELS : HOUSE_TYPES).includes(value) && (
                      <option value={value}>{value}</option>
                    )}
                  </select>
                ) : (
                  <input
                    {...input}
                    inputMode={NUMBER_KEYS.has(key) ? "numeric" : undefined}
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    autoComplete="off"
                  />
                )
              }
            </Vak>
            <Vak
              label="Toelichting"
              hint="Waar komt de waarde vandaan? Bijvoorbeeld NEN 2580-meetrapport of zelf nagemeten bij de bezichtiging."
              error={error?.field === "explanation" ? error.text : undefined}
            >
              {(input) => (
                <input {...input} value={explanation} onChange={(e) => setExplanation(e.target.value)} autoComplete="off" />
              )}
            </Vak>
            {error?.field === "form" && (
              <p role="alert" className="notice error">
                {error.text}
              </p>
            )}
            <div className="dialog-actions">
              {correction && (
                <button type="button" className="destructive correctie-remove" disabled={busy} onClick={remove}>
                  Correctie verwijderen
                </button>
              )}
              <Dialog.Close type="button" disabled={busy}>
                Annuleren
              </Dialog.Close>
              <button type="submit" disabled={busy}>
                Correctie opslaan
              </button>
            </div>
          </form>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
