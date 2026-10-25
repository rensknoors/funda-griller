import { Dialog } from "@base-ui/react/dialog";
import { useState } from "react";

import { type Case, type CasePhoto, type ObservationFact, rerunObservations } from "./api";

const dayMonth = new Intl.DateTimeFormat("nl-NL", { day: "numeric", month: "short" });

export const OBSERVATION_LABELS: Record<string, string> = {
  kitchen_age_years: "Keuken, geschatte leeftijd",
  bathroom_age_years: "Badkamer, geschatte leeftijd",
  damp_or_mould: "Vocht of schimmel zichtbaar",
  roof_condition: "Staat van het dak",
  facade_condition: "Staat van de gevel",
  renovation_needed: "Renovatie nodig",
};

const LEVEL_COPY: Record<string, string> = {
  good: "goed",
  fair: "redelijk",
  poor: "slecht",
  none: "geen",
  cosmetic: "cosmetisch",
  partial: "gedeeltelijk",
  full: "volledig",
};

const STATUS_COPY: Record<Case["observations"]["status"], string | null> = {
  succeeded: null,
  failed: "Analyse van de foto's mislukt; eerdere waarnemingen blijven staan.",
  not_run: "Foto's nog niet geanalyseerd.",
  no_photos: "Geen foto's bij deze advertentie.",
};

/** An Observation's value as shown: always prefixed ≈, because it is a model estimate. */
export function observationValue(key: string, value: unknown): string {
  if (typeof value === "boolean") return `≈ ${value ? "ja" : "nee"}`;
  if (typeof value === "number" && key.endsWith("_age_years")) return `≈ ${value} jaar oud`;
  return `≈ ${LEVEL_COPY[String(value)] ?? String(value)}`;
}

export const photoList = (photos: CasePhoto[]) => photos.map((p) => p.number).join(", ");

/** Foto-waarnemingen: the Listing photos the app keeps and the Observations read from them. */
export function FotoWaarnemingen(props: { data: Case; fundaId: string; onCase: (data: Case) => void }) {
  const { data } = props;
  const observations = data.facts.filter((f): f is ObservationFact => f.provenance === "observation");
  const [viewing, setViewing] = useState<CasePhoto | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const statusCopy = STATUS_COPY[data.observations.status];

  async function rerun() {
    setBusy(true);
    setFailed(false);
    try {
      props.onCase(await rerunObservations(props.fundaId));
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <details open className="fact-group">
      <summary>
        <h3 id="foto-waarnemingen-title">Foto-waarnemingen</h3>
        <span className="muted">
          {observations.length} waarnemingen · {observations.length} geschat
        </span>
      </summary>
      {data.photos.length > 0 && (
        <div className="row photo-strip-row">
          <ul className="photo-strip" aria-label="Foto's van de advertentie">
            {data.photos.map((photo) => (
              <li key={photo.number}>
                <button
                  type="button"
                  className="photo-thumb"
                  aria-label={`Foto ${photo.number} bekijken`}
                  onClick={() => setViewing(photo)}
                >
                  <img src={photo.url} alt={`Foto ${photo.number}`} loading="lazy" />
                </button>
              </li>
            ))}
          </ul>
          <button type="button" className="small" disabled={busy} onClick={rerun}>
            {busy ? "Bezig…" : "Foto's opnieuw analyseren"}
          </button>
        </div>
      )}
      {statusCopy && <p className="empty">{statusCopy}</p>}
      {failed && (
        <p role="alert" className="notice error">
          <span aria-hidden="true">! </span>Opnieuw analyseren mislukt. Probeer het later opnieuw.
        </p>
      )}
      <ol className="facts">
        {observations.map((fact, index) => (
          <li key={fact.key} className="fact">
            <span className="vak-number">{index + 1}</span>
            <span className="fact-label" title={fact.note ?? undefined}>
              {OBSERVATION_LABELS[fact.key] ?? fact.key}
            </span>
            <span className="fact-value">
              {observationValue(fact.key, fact.value)}
              {fact.note && <span className="muted"> · {fact.note}</span>}
            </span>
            <span
              className="stamp stamp-observation"
              aria-label={`Waarneming, geschat door model, uit foto ${photoList(fact.photos)}, ${dayMonth.format(new Date(fact.extracted_at))}`}
            >
              <span aria-hidden="true">◔ OBS</span>{" "}
              {fact.photos.map((photo, i) => (
                <span key={photo.number}>
                  {i === 0 ? "foto " : ", "}
                  <button
                    type="button"
                    className="link"
                    aria-label={`Foto ${photo.number} bekijken`}
                    onClick={() => setViewing(photo)}
                  >
                    {photo.number}
                  </button>
                </span>
              ))}{" "}
              · geschat
            </span>
          </li>
        ))}
      </ol>
      <Dialog.Root open={viewing !== null} onOpenChange={(open) => !open && setViewing(null)}>
        <Dialog.Portal>
          <Dialog.Backdrop className="dialog-backdrop" />
          <Dialog.Popup className="dialog photo-dialog">
            <Dialog.Title>{viewing && `Foto ${viewing.number}`}</Dialog.Title>
            {viewing && <img src={viewing.url} alt={`Foto ${viewing.number}`} />}
            <div className="row">
              <Dialog.Close>Sluiten</Dialog.Close>
            </div>
          </Dialog.Popup>
        </Dialog.Portal>
      </Dialog.Root>
    </details>
  );
}
