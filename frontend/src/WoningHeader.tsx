import { Menu } from "@base-ui/react/menu";
import { ArrowLeft, Camera, Check, ChevronDown, ChevronLeft, ChevronRight, Download } from "lucide-react";
import { type ReactNode, type RefObject, useEffect, useRef, useState } from "react";

import { exportUrl, type CasePhoto, type Listing } from "./api";
import { PhotoViewer } from "./PhotoViewer";
import { href } from "./route";

export type Neighbours = { previous?: Listing; next?: Listing };

const addressOf = (listing: Listing) =>
  listing.snapshots[0].address ?? listing.url;

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
    <>
      <header className="woning-head hero">
        <div className="woning-nav">
          <a className="back-link" href={href({ view: "woningen" })}>
            <ArrowLeft size={16} aria-hidden="true" />
            Terug naar woningen
          </a>
          <div className="stepper" aria-label="Andere woningen" role="group">
            {neighbours.previous ? (
              <a
                href={href({ view: page, fundaId: neighbours.previous.funda_id })}
                title={addressOf(neighbours.previous)}
              >
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
              <a
                href={href({ view: page, fundaId: neighbours.next.funda_id })}
                title={addressOf(neighbours.next)}
              >
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
            <WoningFacts row={listing.comparison} />
            <div className="woning-actions">
              {props.actions}
              <ExportMarkdown fundaId={fundaId} />
            </div>
          </div>
          <HeaderPhotos photos={latest.photos ?? []} />
        </div>
      </header>
      <Halves fundaId={fundaId} page={page} address={addressOf(listing)} />
    </>
  );
}

/** Dossier and Oordeel as tabs on the hero's bottom edge. They pin under the topbar once the hero
 * scrolls past, compact and with the address, so the other half is always one click away. */
function Halves(props: { fundaId: string; page: "dossier" | "oordeel"; address: string }) {
  const { fundaId, page } = props;
  const sentinel = useRef<HTMLDivElement>(null);
  const [stuck, setStuck] = useState(false);
  useEffect(() => {
    const element = sentinel.current;
    if (!element) return;
    const topbar = parseFloat(getComputedStyle(element).getPropertyValue("--topbar-h")) || 0;
    const observer = new IntersectionObserver(
      ([entry]) => setStuck(!entry.isIntersecting && entry.boundingClientRect.top < topbar),
      { rootMargin: `-${topbar}px 0px 0px 0px` },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  return (
    <>
      <div ref={sentinel} className="halves-sentinel" aria-hidden="true" />
      <nav className="halves" aria-label="Woning" data-stuck={stuck ? "" : undefined}>
        <a
          href={href({ view: "dossier", fundaId })}
          aria-current={page === "dossier" ? "page" : undefined}
        >
          Dossier
          <span className="halves-note" aria-hidden="true">
            feiten en bronnen
          </span>
        </a>
        <a
          href={href({ view: "oordeel", fundaId })}
          aria-current={page === "oordeel" ? "page" : undefined}
        >
          Oordeel
          <span className="halves-note" aria-hidden="true">
            uitkomst en biedadvies
          </span>
        </a>
        <span className="halves-address" aria-hidden="true">
          {props.address}
        </span>
      </nav>
    </>
  );
}

/** How many thumbnails sit beside the main photo; the last one opens the rest. */
const THUMBNAILS = 4;

/** The first photo large, the next few in a block beside it: the Woning as funda shows it, opening
 * the viewer. */
function HeaderPhotos({ photos }: { photos: CasePhoto[] }) {
  const [viewing, setViewing] = useState<CasePhoto | null>(null);
  if (photos.length === 0) return null;
  const [first, ...rest] = photos;
  const thumbnails = rest.slice(0, THUMBNAILS);
  const more = photos.length - 1 - thumbnails.length;
  return (
    <div className="header-photos" data-thumbs={thumbnails.length}>
      <button type="button" className="header-photo-main" aria-label="Foto 1 openen" onClick={() => setViewing(first)}>
        <img src={first.url} alt="" />
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
      <span className="card-photo-count">
        <Camera size={13} aria-hidden="true" />
        {photos.length}
        <span className="visually-hidden"> foto's</span>
      </span>
      <PhotoViewer photos={photos} viewing={viewing} onView={setViewing} />
    </div>
  );
}

/** The size and energy label, each left out when missing; the label from the register over the
 * advertentie's, as on the Woning cards. */
function WoningFacts({ row }: { row: Listing["comparison"] }) {
  const { living_area, plot_area, energy_label } = row;
  if (living_area === null && plot_area === null && !energy_label) return null;
  return (
    <p className="woning-facts">
      {living_area !== null && <span>{living_area} m² wonen</span>}
      {plot_area !== null && <span>{plot_area} m² perceel</span>}
      {energy_label && (
        <span
          className={`energy-badge energy-${energy_label.value[0].toLowerCase()}`}
          title={energy_label.official ? "Energielabel uit het register" : "Energielabel volgens de advertentie"}
        >
          <span className="visually-hidden">Energielabel </span>
          {energy_label.value}
        </span>
      )}
    </p>
  );
}

/** Download the Woning's Dossier and current Oordeel as one Markdown file for another LLM chat.
 * The koperprofiel goes along anonymised unless unticked in the menu. */
function ExportMarkdown(props: { fundaId: string }) {
  const [withProfile, setWithProfile] = useState(true);
  return (
    <Menu.Root>
      <Menu.Trigger className="export-trigger">
        <Download size={15} aria-hidden="true" />
        Exporteer als Markdown
        <ChevronDown size={15} aria-hidden="true" />
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Positioner className="menu-positioner" align="start" sideOffset={6}>
          <Menu.Popup className="menu">
            <Menu.CheckboxItem checked={withProfile} onCheckedChange={setWithProfile} closeOnClick={false}>
              <span className="menu-check" aria-hidden="true">
                <Menu.CheckboxItemIndicator>
                  <Check size={15} />
                </Menu.CheckboxItemIndicator>
              </span>
              Koperprofiel meesturen
            </Menu.CheckboxItem>
            <Menu.LinkItem href={exportUrl(props.fundaId, withProfile)} download closeOnClick>
              <span className="menu-check" aria-hidden="true">
                <Download size={15} />
              </span>
              Downloaden
            </Menu.LinkItem>
          </Menu.Popup>
        </Menu.Positioner>
      </Menu.Portal>
    </Menu.Root>
  );
}
