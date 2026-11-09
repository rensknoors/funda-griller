import { useEffect, useRef, useState } from "react";

import {
  fetchRunningCaptures,
  isCaptureError,
  type CaptureError,
  type CaptureStep,
  type Listing,
} from "./api";

export type FetchFailure = Exclude<CaptureError, { kind: "already_captured" }>;

export const ERROR_COPY: Record<FetchFailure["kind"], string> = {
  bad_url: "Ophalen mislukt: ongeldige URL. Plak een funda-link van een koopwoning.",
  listing_removed: "Ophalen mislukt: woning verwijderd. Funda toont deze woning niet meer.",
  provider_blocked: "Ophalen mislukt: aanbieder geblokkeerd. Probeer het later opnieuw.",
  no_response: "Ophalen mislukt: de server reageert niet. Controleer of de backend draait.",
  unknown: "Ophalen mislukt. Probeer het opnieuw.",
};

export const STEP_LABEL: Record<CaptureStep, string> = {
  listing: "Advertentie ophalen",
  photos: "Foto's downloaden",
  sources: "Bronnen raadplegen",
  observations: "Foto's beoordelen",
  brochure: "Brochure lezen",
};

/** A capture or refetch the user started, from its request until the user dismisses it. */
export type Capture = {
  id: number;
  url: string;
  /** Known up front for a refetch; a new capture learns it from the backend. */
  fundaId: string | null;
  /** The address when known, else a name read from the funda-link. */
  name: string;
  step: CaptureStep;
  startedAt: number;
  outcome: { kind: "running" } | { kind: "done"; listing: Listing } | { kind: "failed"; error: FetchFailure };
};

/** How often the view asks the backend which step a running capture is at. */
const POLL_MS = 800;
/** A finished capture's notice leaves by itself; a failed one stays until dismissed. */
const DONE_LINGER_MS = 10_000;

/**
 * Captures run in the background of the whole app, not of one view: the request stays open while
 * the user moves to a Dossier or the Koperprofiel, and the steps come from polling the backend.
 */
export function useCaptures() {
  const [captures, setCaptures] = useState<Capture[]>([]);
  const nextId = useRef(1);
  const anyRunning = captures.some((c) => c.outcome.kind === "running");

  useEffect(() => {
    if (!anyRunning) return;
    let stopped = false;
    const poll = () =>
      fetchRunningCaptures()
        .then((running) => {
          if (stopped) return;
          setCaptures((current) =>
            current.map((capture) => {
              if (capture.outcome.kind !== "running") return capture;
              const match = running.find((r) =>
                capture.fundaId ? r.funda_id === capture.fundaId : r.url === capture.url,
              );
              return match ? { ...capture, fundaId: match.funda_id, step: match.step } : capture;
            }),
          );
        })
        .catch(() => undefined); // The capture's own request reports a dead backend.
    poll();
    const timer = window.setInterval(poll, POLL_MS);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [anyRunning]);

  function update(id: number, change: (capture: Capture) => Capture | null) {
    setCaptures((current) =>
      current.flatMap((capture) => {
        if (capture.id !== id) return [capture];
        const changed = change(capture);
        return changed ? [changed] : [];
      }),
    );
  }

  function dismiss(id: number) {
    update(id, () => null);
  }

  function isRunning(match: { url?: string; fundaId?: string }): boolean {
    return captures.some(
      (c) =>
        c.outcome.kind === "running" &&
        ((match.url !== undefined && c.url === match.url) || (match.fundaId !== undefined && c.fundaId === match.fundaId)),
    );
  }

  /** Run `request` as a tracked capture. A duplicate is not a capture: it leaves no notice. */
  async function start(
    request: () => Promise<Listing | CaptureError>,
    what: { url: string; fundaId: string | null; name: string },
  ): Promise<Listing | CaptureError> {
    const id = nextId.current++;
    setCaptures((current) => [
      ...current,
      { id, ...what, step: "listing", startedAt: Date.now(), outcome: { kind: "running" } },
    ]);
    const result = await request();
    if (!isCaptureError(result)) {
      update(id, (c) => ({ ...c, fundaId: result.funda_id, name: result.snapshots[0].address ?? c.name, outcome: { kind: "done", listing: result } }));
      window.setTimeout(() => dismiss(id), DONE_LINGER_MS);
    } else if (result.kind === "already_captured") {
      dismiss(id);
    } else {
      update(id, (c) => ({ ...c, outcome: { kind: "failed", error: result } }));
    }
    return result;
  }

  return { captures, start, dismiss, isRunning };
}

/** "Buchterweg 15" from https://www.funda.nl/detail/koop/holtum/huis-buchterweg-15/80907644/:
 * the slug before the id, without its kind of house. A name to show until the address is known. */
export function nameFromUrl(url: string): string {
  try {
    const segments = new URL(url).pathname.split("/").filter(Boolean);
    const slug = segments.at(-1)?.match(/^\d+$/) ? segments.at(-2) : segments.at(-1);
    const words = (slug ?? "").split("-").slice(1).join(" ");
    return words ? words[0].toUpperCase() + words.slice(1) : url;
  } catch {
    return url;
  }
}
