import { useEffect, useState } from "react";

import {
  captureListing,
  fetchListings,
  isCaptureError,
  refetchListing,
  type CaptureError,
  type Listing,
} from "./api";
import "./styles.css";

type ApiState = "checking" | "reachable" | "unreachable";
type ListState = "laden" | "klaar" | "fout";

const ERROR_COPY: Record<Exclude<CaptureError["kind"], "already_captured">, string> = {
  bad_url: "Ophalen mislukt: ongeldige URL. Plak een funda-link van een koopwoning.",
  listing_removed: "Ophalen mislukt: woning verwijderd. Funda toont deze advertentie niet meer.",
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
  const [error, setError] = useState<Exclude<CaptureError, { kind: "already_captured" }> | null>(
    null,
  );
  const [duplicateId, setDuplicateId] = useState<string | null>(null);

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

  async function handleCapture(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setDuplicateId(null);
    const result = await captureListing(url);
    setBusy(false);
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
    setBusy(true);
    setError(null);
    const result = await refetchListing(fundaId);
    setBusy(false);
    if (!isCaptureError(result)) {
      upsert(result);
      setDuplicateId(null);
    } else if (result.kind !== "already_captured") {
      setError(result);
    }
  }

  return (
    <main>
      <h1>Funda Griller</h1>
      <form className="vak" onSubmit={handleCapture}>
        <label htmlFor="listing-url">Funda-link</label>
        <div className="vak-row">
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
          <button type="submit" className="primary" disabled={busy}>
            Ophalen
          </button>
        </div>
        {error && (
          <p id="capture-error" role="alert" className="notice error">
            <span aria-hidden="true">! </span>
            {ERROR_COPY[error.kind]}
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

      <h2>Woningen</h2>
      {listState === "laden" && (
        <div className="skeleton" aria-busy="true" aria-label="Woningen laden" />
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
                onRefetch={handleRefetch}
              />
            ))}
          </tbody>
        </table>
      )}
      <p role="status" className="api-state">
        API: {apiState}
      </p>
    </main>
  );
}

function ListingRow({
  listing,
  busy,
  onRefetch,
}: {
  listing: Listing;
  busy: boolean;
  onRefetch: (fundaId: string) => void;
}) {
  const latest = listing.snapshots[0];
  const sold = latest.status === "sold";
  return (
    <tr className={sold ? "sold" : undefined}>
      <th scope="row">
        <span className={sold ? "struck" : undefined}>{latest.address ?? listing.url}</span>
        {latest.city && <span className="muted"> {latest.city}</span>}{" "}
        <span className="chip">{statusLabel(latest.status, latest.raw_status)}</span>
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
