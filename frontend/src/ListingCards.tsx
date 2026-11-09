import { Camera, Clock, House, Ruler, Trees, TrendingDown, TrendingUp } from "lucide-react";

import type { Listing } from "./api";
import { euro, headroomTone, priceTone, signedEuro, signedPercent } from "./format";
import { ListingActions, SignalCounts, addressOf, statusLabel } from "./ListingsTable";
import { TierMark } from "./TierMark";
import { tierOf } from "./comparison";
import { href } from "./route";

/** Woningen as cards, the way funda shows them: the first photo, then the figures a buyer scans
 * first. Every other figure is one click away in the Dossier, or in the list view. */
export function ListingCards(props: {
  listings: Listing[];
  busy: boolean;
  rowErrors: Record<string, string>;
  flashId: string | null;
  onRefetch: (fundaId: string) => void;
  onArchive: (listing: Listing) => void;
  onRestore: (fundaId: string) => void;
  onRerunVerdict: (fundaId: string) => void;
}) {
  return (
    <ul className="listing-cards" aria-label="Woningen">
      {props.listings.map((listing) => (
        <ListingCard
          key={listing.funda_id}
          listing={listing}
          busy={props.busy}
          failure={props.rowErrors[listing.funda_id]}
          flash={props.flashId === listing.funda_id}
          onRefetch={props.onRefetch}
          onArchive={() => props.onArchive(listing)}
          onRestore={props.onRestore}
          onRerunVerdict={props.onRerunVerdict}
        />
      ))}
    </ul>
  );
}

function ListingCard(props: {
  listing: Listing;
  busy: boolean;
  failure: string | undefined;
  flash: boolean;
  onRefetch: (fundaId: string) => void;
  onArchive: () => void;
  onRestore: (fundaId: string) => void;
  onRerunVerdict: (fundaId: string) => void;
}) {
  const { listing } = props;
  const row = listing.comparison;
  const latest = listing.snapshots[0];
  const photos = latest.photos ?? [];
  const address = addressOf(listing);
  const sold = row.status === "sold";
  const tier = tierOf(listing);
  const classes = [
    "listing-card",
    `card-${tier}`,
    sold && "sold",
    row.stale_count > 0 && "stale",
    listing.archived && "archived",
    props.flash && "flash",
  ];

  return (
    <li className={classes.filter(Boolean).join(" ")} aria-label={address}>
      <div className="card-photo">
        {photos.length > 0 ? (
          <img src={photos[0].url} alt="" loading="lazy" />
        ) : (
          <span className="card-no-photo" aria-hidden="true">
            <House size={32} strokeWidth={1.5} />
          </span>
        )}
        <span className="card-tier">
          <TierMark tier={tier} />
        </span>
        <span className="card-actions">
          <ListingActions
            listing={listing}
            busy={props.busy}
            onRefetch={props.onRefetch}
            onArchive={props.onArchive}
            onRestore={props.onRestore}
            onRerunVerdict={props.onRerunVerdict}
          />
        </span>
        {photos.length > 1 && (
          <span className="card-photo-count">
            <Camera size={13} aria-hidden="true" />
            {photos.length}
            <span className="visually-hidden"> foto's</span>
          </span>
        )}
        {row.stale_count > 0 && (
          <span className="chip stale-chip card-stale">
            <Clock size={13} aria-hidden="true" />
            {row.stale_count} verouderd
          </span>
        )}
      </div>
      <div className="card-body">
        <p className="card-price">
          <span className="num">{row.asking_price != null ? euro.format(row.asking_price) : "–"}</span>
          {row.previous_asking_price != null && row.asking_price != null && (
            <span
              className="price-trend"
              title={`Was ${euro.format(row.previous_asking_price)}`}
              aria-label={`${row.asking_price < row.previous_asking_price ? "verlaagd" : "verhoogd"}, was ${euro.format(row.previous_asking_price)}`}
            >
              {row.asking_price < row.previous_asking_price ? (
                <TrendingDown size={16} aria-hidden="true" />
              ) : (
                <TrendingUp size={16} aria-hidden="true" />
              )}
            </span>
          )}
          {row.headroom != null && (
            <span className={`card-headroom num tone-${headroomTone(row.headroom) ?? "none"}`} title="Betaalruimte boven (+) of tekort onder (−) de vraagprijs">
              {signedEuro(row.headroom)} ruimte
            </span>
          )}
        </p>
        <h2 className="card-address">
          <a href={href({ view: "dossier", fundaId: listing.funda_id })}>
            <span className={sold ? "struck" : undefined}>{address}</span>
          </a>
        </h2>
        <p className="address-meta">
          {latest.city && <span className="muted">{latest.city}</span>}
          <span className={`chip status-${row.status}`}>{statusLabel(row.status, latest.raw_status)}</span>
          {row.status_change && <span className="muted">was {statusLabel(row.status_change.from, "")}</span>}
          {latest.entry === "manual" && <span className="chip">Handmatig ingevoerd</span>}
          {listing.archived && <span className="chip">Gearchiveerd</span>}
        </p>
        {row.hard_no_reason ? (
          <p className="hard-no-reason">Deal-breaker: {row.hard_no_reason}</p>
        ) : (
          <p className="card-facts">
            <span title="Woonoppervlak">
              <Ruler size={15} aria-hidden="true" />
              {row.living_area ?? "–"} m²<span className="visually-hidden"> wonen</span>
            </span>
            <span title="Perceel">
              <Trees size={15} aria-hidden="true" />
              {row.plot_area ?? "–"} m²<span className="visually-hidden"> perceel</span>
            </span>
            {row.energy_label && (
              <span
                className={`energy-badge energy-${row.energy_label.value[0].toLowerCase()}`}
                title={row.energy_label.official ? "Energielabel uit het register" : "Energielabel volgens de advertentie"}
              >
                {row.energy_label.value}
              </span>
            )}
          </p>
        )}
        {props.failure && (
          <p role="alert" className="row-error">
            {props.failure}
          </p>
        )}
        <div className="card-foot">
          <span className="signal-counts">
            <SignalCounts counts={row.flag_counts} />
          </span>
          {row.asking_vs_woz_percent != null && (
            <span
              className={`num tone-${priceTone(row.asking_vs_woz_percent) ?? "none"}`}
              title="Vraagprijs boven (+) of onder (−) de laatste WOZ-waarde"
            >
              WOZ {signedPercent(row.asking_vs_woz_percent)}
            </span>
          )}
        </div>
      </div>
    </li>
  );
}
