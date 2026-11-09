import { flushSync } from "react-dom";

import type { Route } from "./route";

/** How one screen becomes the next, named on `<html data-transition>` for the CSS to animate. */
type Kind = "open" | "close" | "half" | "step-next" | "step-previous";

const woningOf = (route: Route) => (route.view === "dossier" || route.view === "oordeel" ? route.fundaId : null);

function kindOf(from: Route, to: Route): Kind | null {
  const a = woningOf(from);
  const b = woningOf(to);
  if (from.view === "woningen" && b) return "open";
  if (a && to.view === "woningen") return "close";
  if (a && a === b) return "half";
  if (a && b) {
    // The stepper link that points at the new Woning is still in the old page and says which way.
    const link = document.querySelector<HTMLElement>(`.stepper a[href="${CSS.escape(window.location.hash)}"]`);
    return link?.dataset.step === "previous" ? "step-previous" : "step-next";
  }
  return null;
}

/** The Woning's photo on whichever screen is showing: its card in the list, or the header. */
const photoFor = (fundaId: string) => document.querySelector<HTMLElement>(`[data-photo-for="${CSS.escape(fundaId)}"]`);

/** Swap the screen inside a view transition, so the Woning's photo travels between its card and
 * the header, and Vorige/Volgende slides the way the step goes. Without the API, or with reduced
 * motion, the screen swaps (or crossfades) as before. */
export function transitionRoute(from: Route, to: Route, update: () => void) {
  if (!document.startViewTransition) return update();
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const kind = reduced ? null : kindOf(from, to);
  const shared = kind === "open" ? woningOf(to) : kind === "close" ? woningOf(from) : null;
  const root = document.documentElement;

  const name = (fundaId: string | null) => {
    const photo = fundaId ? photoFor(fundaId) : null;
    if (photo) photo.style.viewTransitionName = "woning-photo";
    return photo;
  };
  const before = name(shared);
  if (kind) root.dataset.transition = kind;
  let after: HTMLElement | null = null;

  const transition = document.startViewTransition(async () => {
    if (before) before.style.viewTransitionName = "";
    flushSync(update);
    after = name(shared);
    // A card photo is lazy; give it a moment to decode so the photo lands on a picture, not a blank.
    if (after instanceof HTMLImageElement) {
      after.loading = "eager";
      await Promise.race([after.decode().catch(() => {}), new Promise((done) => setTimeout(done, 200))]);
    }
  });
  transition.finished.finally(() => {
    if (after) after.style.viewTransitionName = "";
    delete root.dataset.transition;
  });
}
