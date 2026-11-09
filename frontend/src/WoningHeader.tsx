import { ArrowLeft, Camera, ChevronLeft, ChevronRight, Download } from "lucide-react";
import { type ReactNode, type RefObject, useState } from "react";

import { exportUrl, type CasePhoto, type Listing } from "./api";
import { PhotoViewer } from "./PhotoViewer";
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
      <div className={`woning-title${(latest.photos ?? []).length > 0 ? " with-photos" : ""}`}>
        <div className="woning-title-text">
          <h1 id={`${page}-title`} ref={props.headingRef} tabIndex={-1}>
            <span className="visually-hidden">{title}: </span>
            {addressOf(listing)}
          </h1>
          <div className="woning-meta">
            {latest.city && <span className="woning-city">{latest.city}</span>}
            {props.meta}
          </div>
          <div className="woning-actions">
            {props.actions}
            <ExportMarkdown fundaId={fundaId} />
          </div>
        </div>
        <HeaderPhotos photos={latest.photos ?? []} />
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

/** How many thumbnails sit under the main photo; the last one opens the rest. */
const THUMBNAILS = 4;

/** The first photo large, the next few small: the Woning as funda shows it, opening the viewer. */
function HeaderPhotos({ photos }: { photos: CasePhoto[] }) {
  const [viewing, setViewing] = useState<CasePhoto | null>(null);
  if (photos.length === 0) return null;
  const [first, ...rest] = photos;
  const thumbnails = rest.slice(0, THUMBNAILS);
  const more = photos.length - 1 - thumbnails.length;
  return (
    <div className="header-photos">
      <button type="button" className="header-photo-main" aria-label="Foto 1 openen" onClick={() => setViewing(first)}>
        <img src={first.url} alt="" />
        <span className="card-photo-count">
          <Camera size={13} aria-hidden="true" />
          {photos.length}
          <span className="visually-hidden"> foto's</span>
        </span>
      </button>
      {thumbnails.length > 0 && (
        <ul className="header-thumbs">
          {thumbnails.map((photo, index) => (
            <li key={photo.number}>
              <button type="button" aria-label={`Foto ${photo.number} openen`} onClick={() => setViewing(photo)}>
                <img src={photo.url} alt="" loading="lazy" />
                {index === thumbnails.length - 1 && more > 0 && (
                  <span className="header-thumbs-more" aria-hidden="true">
                    +{more}
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
      <PhotoViewer photos={photos} viewing={viewing} onView={setViewing} />
    </div>
  );
}

/** Download the Woning's Dossier and current Oordeel as one Markdown file for another LLM chat.
 * The koperprofiel goes along anonymised unless unticked. */
function ExportMarkdown(props: { fundaId: string }) {
  const [withProfile, setWithProfile] = useState(true);
  return (
    <div className="export-markdown">
      <a className="button" href={exportUrl(props.fundaId, withProfile)} download>
        <Download size={15} aria-hidden="true" />
        Exporteer als Markdown
      </a>
      <label className="export-profile">
        <input type="checkbox" checked={withProfile} onChange={(event) => setWithProfile(event.target.checked)} />
        Koperprofiel meesturen (geanonimiseerd)
      </label>
    </div>
  );
}
