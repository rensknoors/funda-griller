import { ArrowLeft, ChevronLeft, ChevronRight } from "lucide-react";
import { type ReactNode, type RefObject } from "react";

import type { Listing } from "./api";
import { href } from "./route";

export type Neighbours = { previous?: Listing; next?: Listing };

const addressOf = (listing: Listing) => listing.snapshots[0].address ?? listing.url;

/** The top of a Woning's two pages: back to the list, the address, Dossier and Oordeel as two
 * halves of one Woning, and the step to the neighbouring Woningen. */
export function WoningHeader(props: {
  listing: Listing;
  page: "dossier" | "oordeel";
  neighbours: Neighbours;
  headingRef: RefObject<HTMLHeadingElement | null>;
  meta: ReactNode;
  actions?: ReactNode;
}) {
  const { listing, page, neighbours } = props;
  const latest = listing.snapshots[0];
  const fundaId = listing.funda_id;
  const title = page === "dossier" ? "Dossier" : "Oordeel";
  return (
    <header className="woning-head hero">
      <div className="woning-nav">
        <a className="back-link" href={href({ view: "woningen" })}>
          <ArrowLeft size={16} aria-hidden="true" />
          Terug naar woningen
        </a>
        <div className="stepper" aria-label="Andere woningen" role="group">
          {neighbours.previous ? (
            <a href={href({ view: page, fundaId: neighbours.previous.funda_id })} title={addressOf(neighbours.previous)}>
              <ChevronLeft size={16} aria-hidden="true" />
              Vorige woning
            </a>
          ) : (
            <span aria-disabled="true">
              <ChevronLeft size={16} aria-hidden="true" />
              Vorige woning
            </span>
          )}
          {neighbours.next ? (
            <a href={href({ view: page, fundaId: neighbours.next.funda_id })} title={addressOf(neighbours.next)}>
              Volgende woning
              <ChevronRight size={16} aria-hidden="true" />
            </a>
          ) : (
            <span aria-disabled="true">
              Volgende woning
              <ChevronRight size={16} aria-hidden="true" />
            </span>
          )}
        </div>
      </div>
      <div className="woning-title">
        <div>
          <h1 id={`${page}-title`} ref={props.headingRef} tabIndex={-1}>
            <span className="visually-hidden">{title}: </span>
            {addressOf(listing)}
          </h1>
          <div className="woning-meta">
            {latest.city && <span className="woning-city">{latest.city}</span>}
            {props.meta}
          </div>
        </div>
        {props.actions && <div className="woning-actions">{props.actions}</div>}
      </div>
      <nav className="halves" aria-label="Woning">
        <a href={href({ view: "dossier", fundaId })} aria-current={page === "dossier" ? "page" : undefined}>
          Dossier
          <span className="halves-note" aria-hidden="true">feiten en bronnen</span>
        </a>
        <a href={href({ view: "oordeel", fundaId })} aria-current={page === "oordeel" ? "page" : undefined}>
          Oordeel
          <span className="halves-note" aria-hidden="true">uitkomst en biedadvies</span>
        </a>
      </nav>
    </header>
  );
}
