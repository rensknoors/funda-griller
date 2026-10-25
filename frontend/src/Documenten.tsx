import { Dialog } from "@base-ui/react/dialog";
import { useState } from "react";

import {
  type CaseDocument,
  type FindingFact,
  type FindingTopic,
  analyseDocument,
  documentFileUrl,
  removeDocument,
  replaceDocument,
  uploadDocument,
} from "./api";
import { plural } from "./plural";

export const FINDING_LABELS: Record<FindingTopic, string> = {
  asbestos: "Asbest",
  leak: "Lekkage",
  solar_lease: "Zonnepanelen (lease)",
  erfpacht: "Erfpacht",
  subsidy: "Subsidie",
  stays_or_goes: "Blijft of gaat mee",
  foundation: "Fundering",
  other: "Overig",
};

const UNREAD_REASONS: Record<string, string> = {
  not_a_pdf: "geen PDF",
  encrypted: "beveiligd met een wachtwoord",
  corrupt: "beschadigd bestand",
  missing: "bestand ontbreekt",
  llm_unavailable: "geen taalmodel ingesteld",
  llm_failed: "analyse mislukt",
  download_failed: "funda gaf het bestand niet",
};

const dayMonth = new Intl.DateTimeFormat("nl-NL", { day: "numeric", month: "short" });

/** "door verkoper" stamp: a seller's claim, with the Document and page to check it against. */
export function FindingStamp({ fundaId, finding }: { fundaId: string; finding: FindingFact }) {
  return (
    <a
      className="stamp stamp-finding"
      href={documentFileUrl(fundaId, finding.document_id, finding.page)}
      target="_blank"
      rel="noreferrer"
      aria-label={`Bevinding door verkoper: ${finding.document_name}, pagina ${finding.page}`}
    >
      <span aria-hidden="true">❝ VRK</span> {finding.document_name} p. {finding.page} · door verkoper
    </a>
  );
}

/** Verkoper-informatie: every Finding, quoted, each citing its Document and page. */
export function VerkoperInformatie({ fundaId, findings }: { fundaId: string; findings: FindingFact[] }) {
  return (
    <details open className="fact-group">
      <summary>
        <h3 id="verkoper-informatie-title">Verkoper-informatie</h3>
        <span className="muted">{plural(findings.length, "bevinding", "bevindingen")} · door verkoper</span>
      </summary>
      {findings.length === 0 ? (
        <p className="empty">Nog geen bevindingen. Upload de Vragenlijst of de Lijst van zaken.</p>
      ) : (
        <ol className="facts">
          {findings.map((finding, index) => (
            <li key={`${finding.document_id}-${index}`} className="fact finding">
              <span className="vak-number">{index + 1}</span>
              <span className="fact-label">{FINDING_LABELS[finding.key] ?? finding.key}</span>
              <span className="fact-value">
                “{finding.statement}”
                {!finding.value && <span className="muted"> (niet van toepassing)</span>}
                {!finding.verified && <span className="muted"> (pagina niet te controleren)</span>}
              </span>
              <FindingStamp fundaId={fundaId} finding={finding} />
            </li>
          ))}
        </ol>
      )}
    </details>
  );
}

function statusLine(document: CaseDocument): string {
  const reason = document.reason ? UNREAD_REASONS[document.reason] ?? document.reason : null;
  switch (document.status) {
    case "analysed":
      return `gelezen · ${document.page_count} pagina's · ${plural(document.finding_count, "bevinding", "bevindingen")}`;
    case "unreadable":
      return `kon niet gelezen worden${reason ? ` (${reason})` : ""}`;
    case "not_analysed":
      return `nog niet geanalyseerd${reason ? ` (${reason})` : ""}`;
    case "download_failed":
      return `downloaden mislukt${reason ? ` (${reason})` : ""}`;
    default:
      return "bezig";
  }
}

/** Documenten: upload, list, re-upload and remove a Listing's Documents. Each change rebuilds the
 * Dossier through `onChanged`. */
export function Documenten(props: {
  fundaId: string;
  documents: CaseDocument[];
  onChanged: () => Promise<void>;
}) {
  const { fundaId, documents } = props;
  const [busy, setBusy] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [removeTarget, setRemoveTarget] = useState<CaseDocument | null>(null);

  async function act(label: string, action: () => Promise<void>) {
    setBusy(label);
    setFailed(false);
    try {
      await action();
      await props.onChanged();
    } catch {
      setFailed(true);
    } finally {
      setBusy(null);
    }
  }

  function pickFile(event: React.ChangeEvent<HTMLInputElement>, then: (file: File) => Promise<void>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file) void act("upload", () => then(file));
  }

  return (
    <section aria-labelledby="documenten-title" className="documenten">
      <h3 id="documenten-title">Documenten</h3>
      <p className="muted measure">
        Documenten blijven op deze computer en worden alleen naar het taalmodel gestuurd om
        bevindingen te lezen.
      </p>
      {documents.length === 0 && <p className="empty">Nog geen documenten. Upload de Vragenlijst.</p>}
      <ul className="document-list">
        {documents.map((document) => (
          <li key={document.id} className={`document document-${document.status}`}>
            <span>
              <a href={documentFileUrl(fundaId, document.id)} target="_blank" rel="noreferrer">
                {document.name}
              </a>
              {document.kind === "brochure" && <span className="chip">funda</span>}
              <span className={document.status === "analysed" ? "muted" : "document-problem"}>
                {" "}
                {document.status !== "analysed" && <span aria-hidden="true">! </span>}
                {statusLine(document)}
              </span>
              {document.rejected_findings > 0 && (
                <span className="muted"> · {plural(document.rejected_findings, "bevinding", "bevindingen")} afgewezen (onjuiste pagina of onderwerp)</span>
              )}
            </span>
            <span className="row">
              {(document.status === "not_analysed" || document.status === "download_failed") && (
                <button
                  type="button"
                  className="small"
                  disabled={busy !== null}
                  onClick={() => act("analyse", () => analyseDocument(fundaId, document.id))}
                >
                  {document.status === "download_failed" ? "Opnieuw downloaden" : "Opnieuw analyseren"}
                </button>
              )}
              {document.kind === "upload" && (
                <label className="button small">
                  Opnieuw uploaden
                  <input
                    type="file"
                    accept="application/pdf,.pdf"
                    className="visually-hidden"
                    aria-label={`${document.name} opnieuw uploaden`}
                    disabled={busy !== null}
                    onChange={(event) => pickFile(event, (file) => replaceDocument(fundaId, document.id, file))}
                  />
                </label>
              )}
              <button
                type="button"
                className="small destructive"
                disabled={busy !== null}
                aria-label={`${document.name} verwijderen`}
                onClick={() => setRemoveTarget(document)}
              >
                Verwijderen
              </button>
            </span>
          </li>
        ))}
      </ul>
      <label className="button">
        {busy === "upload" ? "Bezig met lezen…" : "Document uploaden"}
        <input
          type="file"
          accept="application/pdf,.pdf"
          className="visually-hidden"
          aria-label="Document uploaden"
          disabled={busy !== null}
          onChange={(event) => pickFile(event, (file) => uploadDocument(fundaId, file))}
        />
      </label>
      {busy !== null && busy !== "upload" && <span className="muted"> Bezig…</span>}
      {failed && (
        <p role="alert" className="notice error">
          <span aria-hidden="true">! </span>Dat lukte niet. Probeer het opnieuw.
        </p>
      )}

      <Dialog.Root open={removeTarget !== null} onOpenChange={(open) => !open && setRemoveTarget(null)}>
        <Dialog.Portal>
          <Dialog.Backdrop className="dialog-backdrop" />
          <Dialog.Popup className="dialog">
            <Dialog.Title>{removeTarget?.name} verwijderen?</Dialog.Title>
            <Dialog.Description>
              Het bestand wordt van deze computer verwijderd en de bevindingen eruit verdwijnen uit
              het dossier.
            </Dialog.Description>
            <div className="row">
              <button
                type="button"
                className="destructive"
                onClick={() => {
                  const target = removeTarget;
                  setRemoveTarget(null);
                  if (target) void act("remove", () => removeDocument(fundaId, target.id));
                }}
              >
                Verwijderen
              </button>
              <Dialog.Close>Annuleren</Dialog.Close>
            </div>
          </Dialog.Popup>
        </Dialog.Portal>
      </Dialog.Root>
    </section>
  );
}
