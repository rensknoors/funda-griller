import { Dialog } from "@base-ui/react/dialog";
import { Menu } from "@base-ui/react/menu";
import { ArrowDown, ArrowUp, Clock, Ellipsis, Landmark, Newspaper, TrendingDown, TrendingUp } from "lucide-react";
import { useState } from "react";

import type { Listing } from "./api";
import { euro, euroRange, headroomTone, priceTone, signedEuro, signedPercent } from "./format";
import { plural } from "./plural";
import { TierMark } from "./TierMark";
import { href } from "./route";
import { FlagGlyph } from "./FlagGlyph";
import {
  NO_FILTERS,
  TIER_ORDER,
  tierOf,
  visibleListings,
  type Filters,
  type Sort,
  type SortKey,
  type TierKey,
} from "./comparison";

const dateTime = new Intl.DateTimeFormat("nl-NL", { dateStyle: "medium", timeStyle: "short" });

const DEFAULT_SORT: Sort = { key: "tier", direction: "ascending" };

/** Below 720px the table header is hidden; sorting moves to a select. */
const SORT_OPTIONS: [string, string][] = [
  ["tier:ascending", "Oordeel"],
  ["price:ascending", "Vraagprijs oplopend"],
  ["price:descending", "Vraagprijs aflopend"],
  ["woz:ascending", "t.o.v. WOZ"],
  ["headroom:descending", "Ruimte boven vraag"],
  ["stale:descending", "Meest verouderd"],
];

export function ListingsTable(props: {
  listings: Listing[];
  busy: boolean;
  /** Per Listing: why its last refetch failed, in Dutch. */
  rowErrors: Record<string, string>;
  /** The Listing just refetched; its row flashes once. */
  flashId: string | null;
  onRefetch: (fundaId: string) => void;
  onArchive: (fundaId: string) => void;
  onRestore: (fundaId: string) => void;
  /** Make a new Verdict version for this Woning; never happens by itself. */
  onRerunVerdict: (fundaId: string) => void;
}) {
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  const [sort, setSort] = useState<Sort>(DEFAULT_SORT);
  const [archiveTarget, setArchiveTarget] = useState<Listing | null>(null);
  const rows = visibleListings(props.listings, filters, sort);
  const archivedCount = props.listings.filter((l) => l.archived).length;

  function toggleTier(tier: TierKey, on: boolean) {
    setFilters((f) => ({ ...f, tiers: on ? [...f.tiers, tier] : f.tiers.filter((t) => t !== tier) }));
  }

  function sortBy(key: SortKey) {
    setSort((current) =>
      current.key === key
        ? { key, direction: current.direction === "ascending" ? "descending" : "ascending" }
        : { key, direction: "ascending" },
    );
  }

  const header = (key: SortKey, label: React.ReactNode, className?: string, title?: string) => (
    <th scope="col" className={className} aria-sort={sort.key === key ? sort.direction : undefined} title={title}>
      <button type="button" className="sort" onClick={() => sortBy(key)}>
        {label}
        {sort.key === key &&
          (sort.direction === "ascending" ? (
            <ArrowUp size={13} strokeWidth={2.25} aria-hidden="true" className="sort-glyph" />
          ) : (
            <ArrowDown size={13} strokeWidth={2.25} aria-hidden="true" className="sort-glyph" />
          ))}
      </button>
    </th>
  );

  return (
    <>
      <div className="list-filters" role="group" aria-label="Filters">
        <fieldset className="tier-filter">
          <legend>Oordeel</legend>
          {TIER_ORDER.map((tier) => (
            <label key={tier} className="tier-toggle">
              <input
                type="checkbox"
                checked={filters.tiers.includes(tier)}
                onChange={(event) => toggleTier(tier, event.target.checked)}
              />
              <TierMark tier={tier} size="compact" />
            </label>
          ))}
        </fieldset>
        <label className="price-filter">
          Prijs min (€)
          <PriceInput value={filters.minPrice} onChange={(minPrice) => setFilters((f) => ({ ...f, minPrice }))} />
        </label>
        <label className="price-filter">
          Prijs max (€)
          <PriceInput value={filters.maxPrice} onChange={(maxPrice) => setFilters((f) => ({ ...f, maxPrice }))} />
        </label>
        <label>
          <input
            type="checkbox"
            checked={filters.staleOnly}
            onChange={(event) => setFilters((f) => ({ ...f, staleOnly: event.target.checked }))}
          />{" "}
          Alleen verouderd
        </label>
        <label>
          <input
            type="checkbox"
            checked={filters.showArchived}
            onChange={(event) => setFilters((f) => ({ ...f, showArchived: event.target.checked }))}
          />{" "}
          Toon gearchiveerd
        </label>
        <label className="narrow-sort">
          Sorteren
          <select
            value={`${sort.key}:${sort.direction}`}
            onChange={(event) => {
              const [key, direction] = event.target.value.split(":");
              setSort({ key: key as SortKey, direction: direction as Sort["direction"] });
            }}
          >
            {SORT_OPTIONS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <p className="result-count" aria-live="polite">
          {rows.length} {rows.length === 1 ? "woning" : "woningen"}
          {archivedCount > 0 && !filters.showArchived && (
            <>
              {" · "}
              <button
                type="button"
                className="link"
                onClick={() => setFilters((f) => ({ ...f, showArchived: true }))}
              >
                {archivedCount} gearchiveerd
              </button>
            </>
          )}
        </p>
      </div>
      <table aria-label="Woningen" className="listings">
        <thead>
          <tr>
            {header("tier", "Oordeel")}
            <th scope="col">Adres</th>
            {header("price", "Vraagprijs", "num")}
            {header("woz", "t.o.v. WOZ", "num", "Vraagprijs boven (+) of onder (−) de laatste WOZ-waarde")}
            {header(
              "comparables",
              "t.o.v. vergelijkbaar",
              "num col-detail",
              "Vraagprijs per m² boven (+) of onder (−) de mediaan van vergelijkbare woningen",
            )}
            {header("area", "m² woon / perceel", "num col-detail")}
            <th scope="col" className="col-detail">Label</th>
            {header("headroom", "Ruimte boven vraag", "num", "Betaalruimte boven (+) of tekort onder (−) de vraagprijs")}
            {header(
              "renovation",
              "Direct nodig",
              "num col-detail",
              "Geschatte kosten van direct nodig onderhoud (Verbouwingsraming)",
            )}
            <th scope="col" className="col-detail">Signalen</th>
            {header("stale", "Data")}
            <th scope="col">
              <span className="visually-hidden">Acties</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((listing) => (
            <ListingRow
              key={listing.funda_id}
              listing={listing}
              busy={props.busy}
              failure={props.rowErrors[listing.funda_id]}
              flash={props.flashId === listing.funda_id}
              onRefetch={props.onRefetch}
              onArchive={() => setArchiveTarget(listing)}
              onRestore={props.onRestore}
              onRerunVerdict={props.onRerunVerdict}
            />
          ))}
        </tbody>
      </table>
      {rows.length === 0 && (
        <p className="empty">
          Geen woningen binnen deze filters.{" "}
          <button type="button" className="link" onClick={() => setFilters(NO_FILTERS)}>
            Filters wissen
          </button>
        </p>
      )}
      <Dialog.Root open={archiveTarget !== null} onOpenChange={(open) => !open && setArchiveTarget(null)}>
        <Dialog.Portal>
          <Dialog.Backdrop className="dialog-backdrop" />
          <Dialog.Popup className="dialog">
            <Dialog.Title>{archiveTarget && addressOf(archiveTarget)} archiveren?</Dialog.Title>
            <Dialog.Description>
              De woning verdwijnt uit de lijst; momentopnamen en dossier blijven bewaard. Terugzetten
              kan via Toon gearchiveerd.
            </Dialog.Description>
            <div className="dialog-actions">
              <Dialog.Close>Annuleren</Dialog.Close>
              <button
                type="button"
                className="destructive"
                onClick={() => {
                  if (archiveTarget) props.onArchive(archiveTarget.funda_id);
                  setArchiveTarget(null);
                }}
              >
                Archiveren
              </button>
            </div>
          </Dialog.Popup>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
}

function PriceInput({ value, onChange }: { value: number | null; onChange: (value: number | null) => void }) {
  return (
    <input
      type="number"
      inputMode="numeric"
      min={0}
      step={5000}
      value={value ?? ""}
      onChange={(event) => onChange(event.target.value === "" ? null : Number(event.target.value))}
    />
  );
}

function ListingRow(props: {
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
  const sold = row.status === "sold";
  const address = addressOf(listing);
  const classes = [sold && "sold", row.stale_count > 0 && "stale", listing.archived && "archived", props.flash && "flash"];

  function handleKey(event: React.KeyboardEvent<HTMLTableRowElement>) {
    if (event.target !== event.currentTarget) return;
    const sibling =
      event.key === "ArrowDown"
        ? event.currentTarget.nextElementSibling
        : event.key === "ArrowUp"
          ? event.currentTarget.previousElementSibling
          : null;
    if (sibling instanceof HTMLElement) {
      event.preventDefault();
      sibling.focus();
    } else if (event.key === "Enter") {
      window.location.hash = href({ view: "dossier", fundaId: listing.funda_id });
    } else if (event.key === "x" && !listing.archived) {
      props.onArchive();
    }
  }

  return (
    <tr tabIndex={0} className={classes.filter(Boolean).join(" ") || undefined} onKeyDown={handleKey}>
      <td>
        <TierMark tier={tierOf(listing)} />
      </td>
      <th scope="row">
        <a className="address-link" href={href({ view: "dossier", fundaId: listing.funda_id })}>
          <span className={sold ? "struck" : undefined}>{address}</span>
        </a>
        <span className="address-meta">
          {latest.city && <span className="muted">{latest.city}</span>}
          <span className={`chip status-${row.status}`}>{statusLabel(row.status, latest.raw_status)}</span>
          {row.status_change && <span className="muted">was {statusLabel(row.status_change.from, "")}</span>}
          {latest.entry === "manual" && <span className="chip">Handmatig ingevoerd</span>}
          {listing.archived && <span className="chip">Gearchiveerd</span>}
        </span>
        {row.hard_no_reason && <span className="hard-no-reason">Deal-breaker: {row.hard_no_reason}</span>}
        {props.failure && (
          <span role="alert" className="row-error">
            {props.failure}
          </span>
        )}
      </th>
      <td className="num" data-label="Vraagprijs">
        {row.asking_price != null ? euro.format(row.asking_price) : "–"}
        {row.previous_asking_price != null && row.asking_price != null && (
          <span
            className="price-trend"
            title={`Was ${euro.format(row.previous_asking_price)}`}
            aria-label={`${row.asking_price < row.previous_asking_price ? "verlaagd" : "verhoogd"}, was ${euro.format(row.previous_asking_price)}`}
          >
            {row.asking_price < row.previous_asking_price ? (
              <TrendingDown size={14} aria-hidden="true" className="inline-icon" />
            ) : (
              <TrendingUp size={14} aria-hidden="true" className="inline-icon" />
            )}
          </span>
        )}
      </td>
      <td className={`num tone-${priceTone(row.asking_vs_woz_percent) ?? "none"}`} data-label="t.o.v. WOZ">
        {signedPercent(row.asking_vs_woz_percent)}
      </td>
      <td className={`num col-detail tone-${priceTone(row.asking_vs_comparables_percent) ?? "none"}`}>
        {signedPercent(row.asking_vs_comparables_percent)}
      </td>
      <td className="num col-detail">
        {row.living_area ?? "–"} / {row.plot_area ?? "–"}
      </td>
      <td className="col-detail">
        {row.energy_label ? (
          <>
            <span className="energy-badge">{row.energy_label.value}</span>
            {row.energy_label.official ? (
              <Landmark size={14} aria-hidden="true" className="label-source" />
            ) : (
              <Newspaper size={14} aria-hidden="true" className="label-source" />
            )}
            <span className="visually-hidden">
              {row.energy_label.official ? "uit het energielabelregister" : "volgens de advertentie"}
            </span>
          </>
        ) : (
          "–"
        )}
      </td>
      <td className={`num tone-${headroomTone(row.headroom) ?? "none"}`} data-label="Ruimte boven vraag">{row.headroom != null ? signedEuro(row.headroom) : "–"}</td>
      <td className="num col-detail" data-label="Direct nodig">
        {row.renovation_direct
          ? row.renovation_direct.high > 0
            ? euroRange(row.renovation_direct.low, row.renovation_direct.high)
            : "geen"
          : "–"}
      </td>
      <td className="col-detail signal-counts">
        {(["pro", "con", "risk"] as const).map((flagClass) => {
          const count = row.flag_counts[flagClass];
          const [one, many] = { pro: ["pluspunt", "pluspunten"], con: ["minpunt", "minpunten"], risk: ["risico", "risico's"] }[flagClass];
          return (
            <span key={flagClass} className={`signal-count${count === 0 ? " zero" : ""}`}>
              <FlagGlyph flagClass={flagClass} />
              <span aria-hidden="true">{count}</span>
              <span className="visually-hidden">{plural(count, one, many)}</span>
            </span>
          );
        })}
      </td>
      <td>
        {row.stale_count > 0 && (
          <span className="chip stale-chip">
            <Clock size={13} aria-hidden="true" />
            {row.stale_count} verouderd
          </span>
        )}
        <span className="muted fetched-at">{dateTime.format(new Date(row.last_fetched_at))}</span>
      </td>
      <td>
        <Menu.Root>
          <Menu.Trigger className="row-menu" aria-label="Acties" disabled={props.busy}>
            <Ellipsis size={18} aria-hidden="true" />
          </Menu.Trigger>
          <Menu.Portal>
            <Menu.Positioner align="end">
              <Menu.Popup className="menu">
                <Menu.Item onClick={() => props.onRefetch(listing.funda_id)}>Opnieuw ophalen</Menu.Item>
                <Menu.Item onClick={() => props.onRerunVerdict(listing.funda_id)}>
                  Oordeel opnieuw draaien
                </Menu.Item>
                {listing.archived ? (
                  <Menu.Item onClick={() => props.onRestore(listing.funda_id)}>Terugzetten</Menu.Item>
                ) : (
                  <Menu.Item onClick={props.onArchive}>Archiveren</Menu.Item>
                )}
              </Menu.Popup>
            </Menu.Positioner>
          </Menu.Portal>
        </Menu.Root>
      </td>
    </tr>
  );
}

function addressOf(listing: Listing): string {
  return listing.snapshots[0].address ?? listing.url;
}

export function statusLabel(status: string, raw: string): string {
  if (status === "available") return "Beschikbaar";
  if (status === "negotiations") return "Onder bod";
  if (status === "sold") return "Verkocht";
  return raw || "Onbekend";
}
