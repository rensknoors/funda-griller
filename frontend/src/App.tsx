import { useEffect, useState } from "react";

import { BuyerProfileForm } from "./BuyerProfileForm";
import { CaseView } from "./CaseView";
import { ManualEntryForm } from "./ManualEntryForm";
import { VerdictView } from "./VerdictView";
import {
  captureListing,
  fetchListings,
  isCaptureError,
  refetchListing,
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

const euro = new Intl.NumberFormat("nl-NL", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});
const dateTime = new Intl.DateTimeFormat("nl-NL", { dateStyle: "medium", timeStyle: "short" });

export function App() {
  const [apiState, setApiState] = useState<ApiState>("checking");
  const [listState, setListState] = useState<ListState>("laden");
  const [listings, setListings] = useState<Listing[]>([]);
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<FetchFailure | null>(null);
  const [rowErrors, setRowErrors] = useState<Record<string, FetchFailure>>({});
  const [duplicateId, setDuplicateId] = useState<string | null>(null);
  const [openCaseId, setOpenCaseId] = useState<string | null>(null);
  const [manualUrl, setManualUrl] = useState<string | null>(null);
  const [verdictOpen, setVerdictOpen] = useState(false);
  const [focusFlagId, setFocusFlagId] = useState<string | null>(null);

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
    } else if (result.kind !== "already_captured") {
      setRowErrors((current) => ({ ...current, [fundaId]: result }));
    }
  }

  const openCase = listings.find((l) => l.funda_id === openCaseId);
  if (openCase && verdictOpen) {
    return (
      <main>
        <h1>Funda Griller</h1>
        <VerdictView
          listing={openCase}
          onBackToCase={() => {
            setFocusFlagId(null);
            setVerdictOpen(false);
          }}
          onShowFlag={(flagId) => {
            setFocusFlagId(flagId);
            setVerdictOpen(false);
          }}
        />
      </main>
    );
  }
  if (openCase) {
    return (
      <main>
        <h1>Funda Griller</h1>
        <CaseView
          listing={openCase}
          busy={busy}
          onClose={() => {
            setFocusFlagId(null);
            setOpenCaseId(null);
          }}
          onRefetch={handleRefetch}
          onOpenVerdict={() => setVerdictOpen(true)}
          focusFlagId={focusFlagId}
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
      {listState === "klaar" && listings.length > 0 && (
        <table>
          <thead>
            <tr>
              <th scope="col">Adres</th>
              <th scope="col" className="num">Vraagprijs</th>
              <th scope="col" className="num">m² woon / perceel</th>
              <th scope="col">Label</th>
              <th scope="col">Laatst opgehaald</th>
              <th scope="col">
                <span className="visually-hidden">Acties</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {listings.map((listing) => (
              <ListingRow
                key={listing.funda_id}
                listing={listing}
                busy={busy}
                failure={rowErrors[listing.funda_id]}
                onRefetch={handleRefetch}
                onOpen={setOpenCaseId}
              />
            ))}
          </tbody>
        </table>
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

function ListingRow({
  listing,
  busy,
  failure,
  onRefetch,
  onOpen,
}: {
  listing: Listing;
  busy: boolean;
  failure: FetchFailure | undefined;
  onRefetch: (fundaId: string) => void;
  onOpen: (fundaId: string) => void;
}) {
  const latest = listing.snapshots[0];
  const sold = latest.status === "sold";
  return (
    <tr className={sold ? "sold" : undefined}>
      <th scope="row">
        <button type="button" className="link" onClick={() => onOpen(listing.funda_id)}>
          <span className={sold ? "struck" : undefined}>{latest.address ?? listing.url}</span>
        </button>
        {latest.city && <span className="muted"> {latest.city}</span>}{" "}
        <span className="chip">{statusLabel(latest.status, latest.raw_status)}</span>
        {latest.entry === "manual" && <>{" "}<span className="chip">Handmatig ingevoerd</span></>}
        {failure && (
          <span role="alert" className="row-error">
            <span aria-hidden="true">! </span>
            {ERROR_COPY[failure.kind]}
          </span>
        )}
      </th>
      <td className="num">{latest.asking_price != null ? euro.format(latest.asking_price) : "–"}</td>
      <td className="num">
        {latest.living_area ?? "–"} / {latest.plot_area ?? "–"}
      </td>
      <td>{latest.energy_label ?? "–"}</td>
      <td>
        {dateTime.format(new Date(latest.fetched_at))}
        {listing.snapshots.length > 1 && (
          <span className="muted"> · {listing.snapshots.length} momentopnames</span>
        )}
      </td>
      <td>
        <button type="button" disabled={busy} onClick={() => onRefetch(listing.funda_id)}>
          Opnieuw ophalen
        </button>
      </td>
    </tr>
  );
}

function statusLabel(status: string, raw: string): string {
  if (status === "available") return "Beschikbaar";
  if (status === "negotiations") return "Onder bod";
  if (status === "sold") return "Verkocht";
  return raw || "Onbekend";
}
