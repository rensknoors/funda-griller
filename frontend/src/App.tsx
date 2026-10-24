import { useEffect, useState } from "react";

import { BuyerProfileForm } from "./BuyerProfileForm";
import { CaseView } from "./CaseView";
import { ListingsTable } from "./ListingsTable";
import { ManualEntryForm } from "./ManualEntryForm";
import {
  archiveListing,
  captureListing,
  fetchListings,
  isCaptureError,
  refetchListing,
  restoreListing,
  type CaptureError,
  type Listing,
} from "./api";

type ApiState = "checking" | "reachable" | "unreachable";
type ListState = "laden" | "klaar" | "fout";

type FetchFailure = Exclude<CaptureError, { kind: "already_captured" }>;

const ERROR_COPY: Record<FetchFailure["kind"], string> = {
  bad_url: "Ophalen mislukt: ongeldige URL. Plak een funda-link van een koopwoning.",
  listing_removed: "Ophalen mislukt: woning verwijderd. Funda toont deze woning niet meer.",
  provider_blocked: "Ophalen mislukt: aanbieder geblokkeerd. Probeer het later opnieuw.",
  unknown: "Ophalen mislukt. Probeer het opnieuw.",
};

export function App() {
  const [apiState, setApiState] = useState<ApiState>("checking");
  const [listState, setListState] = useState<ListState>("laden");
  const [listings, setListings] = useState<Listing[]>([]);
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<FetchFailure | null>(null);
  const [rowErrors, setRowErrors] = useState<Record<string, string>>({});
  const [duplicateId, setDuplicateId] = useState<string | null>(null);
  const [flashId, setFlashId] = useState<string | null>(null);
  const [openCaseId, setOpenCaseId] = useState<string | null>(null);
  const [manualUrl, setManualUrl] = useState<string | null>(null);
  const [archiveFailed, setArchiveFailed] = useState(false);

  useEffect(() => {
    fetch("/api/health")
      .then((response) => response.json())
      .then((body) => setApiState(body.status === "ok" ? "reachable" : "unreachable"))
      .catch(() => setApiState("unreachable"));
    fetchListings()
      .then((loaded) => {
        setListings(loaded);
        setListState("klaar");
      })
      .catch(() => setListState("fout"));
  }, []);

  function upsert(updated: Listing) {
    setListings((current) =>
      current.some((l) => l.funda_id === updated.funda_id)
        ? current.map((l) => (l.funda_id === updated.funda_id ? updated : l))
        : [updated, ...current],
    );
  }

  async function run(request: () => Promise<Listing | CaptureError>) {
    setBusy(true);
    setError(null);
    setDuplicateId(null);
    const result = await request();
    setBusy(false);
    return result;
  }

  async function handleCapture(event: React.FormEvent) {
    event.preventDefault();
    const result = await run(() => captureListing(url));
    if (!isCaptureError(result)) {
      upsert(result);
      setUrl("");
    } else if (result.kind === "already_captured") {
      setDuplicateId(result.fundaId);
    } else {
      setError(result);
    }
  }

  async function handleRefetch(fundaId: string) {
    const result = await run(() => refetchListing(fundaId));
    setRowErrors(({ [fundaId]: _cleared, ...rest }) => rest);
    if (!isCaptureError(result)) {
      upsert(result);
      setFlashId(null);
      requestAnimationFrame(() => setFlashId(fundaId));
    } else if (result.kind !== "already_captured") {
      setRowErrors((current) => ({ ...current, [fundaId]: ERROR_COPY[result.kind] }));
    }
  }

  async function handleArchive(fundaId: string, archived: boolean) {
    setArchiveFailed(false);
    try {
      upsert(await (archived ? archiveListing(fundaId) : restoreListing(fundaId)));
    } catch {
      setArchiveFailed(true);
    }
  }

  const openCase = listings.find((l) => l.funda_id === openCaseId);
  if (openCase) {
    return (
      <main>
        <h1>Funda Griller</h1>
        <CaseView
          listing={openCase}
          busy={busy}
          onClose={() => setOpenCaseId(null)}
          onRefetch={handleRefetch}
        />
      </main>
    );
  }

  return (
    <main>
      <h1>Funda Griller</h1>
      <form className="capture" onSubmit={handleCapture}>
        <label htmlFor="listing-url">Funda-link</label>
        <div className="capture-row">
          <input
            id="listing-url"
            type="url"
            required
            value={url}
            placeholder="https://www.funda.nl/detail/koop/…"
            onChange={(event) => setUrl(event.target.value)}
            aria-describedby={error ? "capture-error" : undefined}
            aria-invalid={error ? true : undefined}
          />
          <button type="submit" disabled={busy}>
            Ophalen
          </button>
        </div>
        {error && (
          <p id="capture-error" role="alert" className="notice error">
            <span aria-hidden="true">! </span>
            {ERROR_COPY[error.kind]}
            {error.kind === "provider_blocked" && manualUrl === null && (
              <>
                {" "}
                <button type="button" onClick={() => setManualUrl(url)}>
                  Handmatig invoeren
                </button>
              </>
            )}
          </p>
        )}
        {duplicateId && (
          <p role="status" className="notice">
            Al in je lijst.{" "}
            <button type="button" onClick={() => handleRefetch(duplicateId)} disabled={busy}>
              Opnieuw ophalen
            </button>
          </p>
        )}
      </form>
      {manualUrl !== null && (
        <ManualEntryForm
          url={manualUrl}
          onSaved={(listing) => {
            upsert(listing);
            setManualUrl(null);
            setError(null);
            setUrl("");
          }}
          onDuplicate={(fundaId) => {
            setManualUrl(null);
            setError(null);
            setDuplicateId(fundaId);
          }}
          onCancel={() => setManualUrl(null)}
        />
      )}

      <h2>Woningen</h2>
      {listState === "laden" && (
        <div className="skeleton" aria-busy="true">
          <span className="visually-hidden">Woningen laden</span>
          <div className="skeleton-row" />
          <div className="skeleton-row" />
          <div className="skeleton-row" />
        </div>
      )}
      {listState === "fout" && (
        <p role="alert" className="notice error">
          <span aria-hidden="true">! </span>Woningen laden mislukt. Ververs de pagina om het opnieuw
          te proberen.
        </p>
      )}
      {listState === "klaar" && listings.length === 0 && (
        <p className="empty">
          Nog geen woningen. Plak hierboven een funda-link en kies Ophalen: de advertentie wordt
          opgehaald en als momentopname bewaard. Daarna staat de woning in deze lijst.
        </p>
      )}
      {archiveFailed && (
        <p role="alert" className="notice error">
          <span aria-hidden="true">! </span>Archiveren of terugzetten mislukt. Probeer het opnieuw.
        </p>
      )}
      {listState === "klaar" && listings.length > 0 && (
        <ListingsTable
          listings={listings}
          busy={busy}
          rowErrors={rowErrors}
          flashId={flashId}
          onOpen={setOpenCaseId}
          onRefetch={handleRefetch}
          onArchive={(fundaId) => handleArchive(fundaId, true)}
          onRestore={(fundaId) => handleArchive(fundaId, false)}
        />
      )}
      <p role="status" className="api-state">
        API: {apiState}
      </p>
      <div className="profile">
        <BuyerProfileForm />
      </div>
    </main>
  );
}
