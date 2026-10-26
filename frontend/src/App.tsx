import { useEffect, useRef, useState } from "react";

import { BuyerProfileForm } from "./BuyerProfileForm";
import { CaseView } from "./CaseView";
import { ListingsTable } from "./ListingsTable";
import { ManualEntryForm } from "./ManualEntryForm";
import { VerdictView } from "./VerdictView";
import {
  apiFetch,
  archiveListing,
  captureListing,
  fetchListings,
  isCaptureError,
  refetchListing,
  restoreListing,
  isVerdictError,
  runVerdict,
  type CaptureError,
  type Listing,
  type VerdictError,
} from "./api";
import { NO_FILTERS, visibleListings } from "./comparison";
import { type Route, href, parseRoute } from "./route";

type ApiState = "checking" | "reachable" | "unreachable";
type ListState = "laden" | "klaar" | "fout";

type FetchFailure = Exclude<CaptureError, { kind: "already_captured" }>;

const ERROR_COPY: Record<FetchFailure["kind"], string> = {
  bad_url: "Ophalen mislukt: ongeldige URL. Plak een funda-link van een koopwoning.",
  listing_removed: "Ophalen mislukt: woning verwijderd. Funda toont deze woning niet meer.",
  provider_blocked: "Ophalen mislukt: aanbieder geblokkeerd. Probeer het later opnieuw.",
  no_response: "Ophalen mislukt: de server reageert niet. Controleer of de backend draait.",
  unknown: "Ophalen mislukt. Probeer het opnieuw.",
};

const VERDICT_ERROR_COPY: Record<VerdictError["kind"], string> = {
  no_buyer_profile: "Oordeel niet gemaakt: vul eerst je koperprofiel in.",
  invalid_verdict: "Oordeel niet gemaakt: het model gaf een ongeldig antwoord.",
  llm_unavailable: "Oordeel niet gemaakt: het model is niet bereikbaar.",
  unknown: "Oordeel niet gemaakt. Probeer het opnieuw.",
};

/** The view follows the URL hash, so the browser's back button and reload keep the user's place. */
function useRoute(): Route {
  const [route, setRoute] = useState(() => parseRoute(window.location.hash));
  useEffect(() => {
    const onChange = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

export function App() {
  const route = useRoute();
  const [apiState, setApiState] = useState<ApiState>("checking");
  const [listState, setListState] = useState<ListState>("laden");
  const [listings, setListings] = useState<Listing[]>([]);
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<FetchFailure | null>(null);
  const [rowErrors, setRowErrors] = useState<Record<string, string>>({});
  const [duplicateId, setDuplicateId] = useState<string | null>(null);
  const [flashId, setFlashId] = useState<string | null>(null);
  const [manualUrl, setManualUrl] = useState<string | null>(null);
  const [focusFlagId, setFocusFlagId] = useState<string | null>(null);
  const [archiveFailed, setArchiveFailed] = useState(false);
  const previousView = useRef<Route["view"] | null>(null);

  // In-page links (a Signaal's "Zie vak 3", the Dossier contents) scroll instead of changing the route.
  useEffect(() => {
    function onClick(event: MouseEvent) {
      const link = (event.target as Element).closest?.("a[href^='#']");
      const target = link?.getAttribute("href") ?? "";
      if (!link || target.startsWith("#/") || target === "#") return;
      const element = document.getElementById(decodeURIComponent(target.slice(1)));
      if (!element) return;
      event.preventDefault();
      element.scrollIntoView({ block: "start" });
      element.classList.remove("targeted");
      requestAnimationFrame(() => element.classList.add("targeted"));
    }
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, []);

  useEffect(() => {
    apiFetch("/api/health")
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

  function reloadListings() {
    fetchListings().then(setListings).catch(() => setListState("fout"));
  }

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

  async function handleRerunVerdict(fundaId: string) {
    setBusy(true);
    setRowErrors(({ [fundaId]: _cleared, ...rest }) => rest);
    const result = await runVerdict(fundaId);
    if (isVerdictError(result)) {
      const reason = result.kind === "llm_unavailable" && result.reason ? ` (${result.reason})` : "";
      setRowErrors((current) => ({ ...current, [fundaId]: VERDICT_ERROR_COPY[result.kind] + reason }));
    } else {
      try {
        setListings(await fetchListings());
        setFlashId(null);
        requestAnimationFrame(() => setFlashId(fundaId));
      } catch {
        setListState("fout");
      }
    }
    setBusy(false);
  }

  const openId = route.view === "dossier" || route.view === "oordeel" ? route.fundaId : null;
  const openCase = listings.find((l) => l.funda_id === openId);
  // Vorige and Volgende step through the list in its default order.
  const ordered = visibleListings(listings, NO_FILTERS, { key: "tier", direction: "ascending" });
  const position = ordered.findIndex((l) => l.funda_id === openId);
  const neighbours = {
    previous: position > 0 ? ordered[position - 1] : undefined,
    next: position >= 0 && position < ordered.length - 1 ? ordered[position + 1] : undefined,
  };

  useEffect(() => {
    if (route.view === "woningen") document.title = "Woningen · Funda Griller";
    if (route.view === "koperprofiel") document.title = "Koperprofiel · Funda Griller";
    // A Signaal jump only holds for the Dossier it was made for.
    if (route.view !== "dossier") setFocusFlagId(null);
    // An Oordeel made from the Dossier changes the row's tier.
    if (route.view === "woningen" && previousView.current !== null) reloadListings();
    previousView.current = route.view;
    window.scrollTo(0, 0);
  }, [route.view, openId]);

  let content: React.ReactNode;
  if (openCase && route.view === "oordeel") {
    content = (
      <VerdictView
        listing={openCase}
        neighbours={neighbours}
        onShowFlag={(flagId) => {
          setFocusFlagId(flagId);
          window.location.hash = href({ view: "dossier", fundaId: openCase.funda_id });
        }}
      />
    );
  } else if (openCase) {
    content = (
      <CaseView
        listing={openCase}
        neighbours={neighbours}
        busy={busy}
        onRefetch={handleRefetch}
        focusFlagId={focusFlagId}
      />
    );
  } else if (openId && listState === "laden") {
    content = (
      <div className="skeleton" aria-busy="true">
        <span className="visually-hidden">Woning laden</span>
        <div className="skeleton-row" />
        <div className="skeleton-row" />
        <div className="skeleton-row" />
      </div>
    );
  } else if (route.view === "koperprofiel") {
    content = <BuyerProfileForm onSaved={reloadListings} />;
  } else {
    content = (
      <>
        <div className="hero">
          <div className="page-head">
            <h1 id="woningen">Woningen</h1>
            <p className="page-lede">Elke woning die je ophaalt krijgt een dossier en, op jouw verzoek, een oordeel.</p>
          </div>
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
                {ERROR_COPY[error.kind]}
                {error.kind === "provider_blocked" && manualUrl === null && (
                  <>
                    {" "}
                    <button type="button" className="small" onClick={() => setManualUrl(url)}>
                      Handmatig invoeren
                    </button>
                  </>
                )}
              </p>
            )}
            {duplicateId && (
              <p role="status" className="notice">
                Al in je lijst.{" "}
                <button type="button" className="small" onClick={() => handleRefetch(duplicateId)} disabled={busy}>
                  Opnieuw ophalen
                </button>
              </p>
            )}
          </form>
        </div>
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
            Woningen laden mislukt. Ververs de pagina om het opnieuw te proberen.
          </p>
        )}
        {listState === "klaar" && listings.length === 0 && (
          <div className="empty-state">
            <p>
              <strong>Nog geen woningen.</strong> Plak hierboven een funda-link en kies Ophalen: de
              advertentie wordt opgehaald en als momentopname bewaard. Daarna staat de woning in deze lijst.
            </p>
            <p>
              Vul ook je <a href={href({ view: "koperprofiel" })}>koperprofiel</a> in, dan zie je per woning je
              betaalruimte.
            </p>
          </div>
        )}
        {archiveFailed && (
          <p role="alert" className="notice error">
            Archiveren of terugzetten mislukt. Probeer het opnieuw.
          </p>
        )}
        {listState === "klaar" && listings.length > 0 && (
          <ListingsTable
            listings={listings}
            busy={busy}
            rowErrors={rowErrors}
            flashId={flashId}
            onRefetch={handleRefetch}
            onArchive={(fundaId) => handleArchive(fundaId, true)}
            onRestore={(fundaId) => handleArchive(fundaId, false)}
            onRerunVerdict={handleRerunVerdict}
          />
        )}
      </>
    );
  }

  const section = route.view === "koperprofiel" ? "koperprofiel" : "woningen";
  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <a className="wordmark" href={href({ view: "woningen" })}>
            <span className="wordmark-mark" aria-hidden="true" />
            Funda Griller
          </a>
          <nav aria-label="Hoofdmenu" className="main-nav">
            <a href={href({ view: "woningen" })} aria-current={section === "woningen" ? "page" : undefined}>
              Woningen
            </a>
            <a href={href({ view: "koperprofiel" })} aria-current={section === "koperprofiel" ? "page" : undefined}>
              Koperprofiel
            </a>
          </nav>
          <p role="status" className={`api-state api-${apiState}`}>
            API: {apiState}
          </p>
        </div>
      </header>
      <main>{content}</main>
    </div>
  );
}
