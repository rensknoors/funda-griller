import { Dialog } from "@base-ui/react/dialog";
import { Menu } from "@base-ui/react/menu";
import { ArrowDown, ArrowUp, ChevronDown, Clock, Ellipsis, LayoutGrid, Landmark, List, Newspaper, TrendingDown, TrendingUp } from "lucide-react";
import { useState, type ReactNode } from "react";

import type { Listing } from "./api";
import { euro, euroRange, headroomTone, priceTone, signedEuro, signedPercent } from "./format";
import { plural } from "./plural";
import { ListingCards } from "./ListingCards";
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

/** The table sorts by Oordeel and Vraagprijs from its header; every other figure sits in a row's
 * details, so it sorts from this select. */
const SORT_OPTIONS: [string, string][] = [
  ["tier:ascending", "Oordeel"],
  ["tier:descending", "Oordeel, omgekeerd"],
  ["price:ascending", "Vraagprijs oplopend"],
  ["price:descending", "Vraagprijs aflopend"],
  ["woz:ascending", "t.o.v. WOZ"],
  ["comparables:ascending", "t.o.v. vergelijkbaar"],
  ["area:descending", "Woonoppervlak"],
  ["headroom:descending", "Ruimte boven vraag"],
  ["renovation:ascending", "Direct nodig"],
  ["stale:descending", "Meest verouderd"],
];

type View = "kaarten" | "lijst";
const VIEW_KEY = "funda-griller:woningen-weergave";

/** Cards by default; the list for comparing figures side by side. Remembered per browser. */
function useView(): [View, (view: View) => void] {
  const [view, setView] = useState<View>(() => {
    try {
      return localStorage.getItem(VIEW_KEY) === "lijst" ? "lijst" : "kaarten";
    } catch {
      return "kaarten";
    }
  });
  function choose(next: View) {
    setView(next);
    try {
      localStorage.setItem(VIEW_KEY, next);
    } catch {
      // Not remembered; the choice still holds for this visit.
    }
  }
  return [view, choose];
}

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
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(new Set());
  const [view, setView] = useView();
  const rows = visibleListings(props.listings, filters, sort);
  const archivedCount = props.listings.filter((l) => l.archived).length;

  function toggleTier(tier: TierKey, on: boolean) {
    setFilters((f) => ({ ...f, tiers: on ? [...f.tiers, tier] : f.tiers.filter((t) => t !== tier) }));
  }

  function toggleExpanded(fundaId: string, open: boolean) {
    setExpanded((current) => {
      const next = new Set(current);
      if (open) next.add(fundaId);
      else next.delete(fundaId);
      return next;
    });
  }

  const allExpanded = rows.length > 0 && rows.every((l) => expanded.has(l.funda_id));

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
        <label className="sort-select">
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
        <div className="view-switch" role="group" aria-label="Weergave">
          <button type="button" aria-pressed={view === "kaarten"} onClick={() => setView("kaarten")}>
            <LayoutGrid size={16} aria-hidden="true" />
            Kaarten
          </button>
          <button type="button" aria-pressed={view === "lijst"} onClick={() => setView("lijst")}>
            <List size={16} aria-hidden="true" />
            Lijst
          </button>
        </div>
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
      {view === "kaarten" ? (
        <ListingCards
          listings={rows}
          busy={props.busy}
          rowErrors={props.rowErrors}
          flashId={props.flashId}
          onRefetch={props.onRefetch}
          onArchive={setArchiveTarget}
          onRestore={props.onRestore}
          onRerunVerdict={props.onRerunVerdict}
        />
      ) : (
        <table aria-label="Woningen" className="listings">
          <thead>
            <tr>
              {header("tier", "Oordeel")}
              <th scope="col">Adres</th>
              {header("price", "Vraagprijs", "num")}
              <th scope="col">Signalen</th>
              <th scope="col" className="expand-col">
                <button
                  type="button"
                  className="expand-all"
                  aria-pressed={allExpanded}
                  onClick={() => setExpanded(allExpanded ? new Set() : new Set(rows.map((l) => l.funda_id)))}
                >
                  {allExpanded ? "Alles inklappen" : "Alles uitklappen"}
                </button>
              </th>
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
                expanded={expanded.has(listing.funda_id)}
                onToggle={(open) => toggleExpanded(listing.funda_id, open)}
                onRefetch={props.onRefetch}
                onArchive={() => setArchiveTarget(listing)}
                onRestore={props.onRestore}
                onRerunVerdict={props.onRerunVerdict}
              />
            ))}
          </tbody>
        </table>
      )}
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
  expanded: boolean;
  onToggle: (open: boolean) => void;
  onRefetch: (fundaId: string) => void;
  onArchive: () => void;
  onRestore: (fundaId: string) => void;
  onRerunVerdict: (fundaId: string) => void;
}) {
  const { listing, expanded } = props;
  const row = listing.comparison;
  const latest = listing.snapshots[0];
  const sold = row.status === "sold";
  const address = addressOf(listing);
  const detailsId = `details-${listing.funda_id}`;
  const classes = [
    sold && "sold",
    row.stale_count > 0 && "stale",
    listing.archived && "archived",
    props.flash && "flash",
    expanded && "expanded",
  ];

  function handleKey(event: React.KeyboardEvent<HTMLTableRowElement>) {
    if (event.target !== event.currentTarget) return;
    const step = event.key === "ArrowDown" ? 1 : event.key === "ArrowUp" ? -1 : 0;
    if (step !== 0) {
      // Skip the details rows: only the Woning rows take focus.
      let sibling: Element | null = event.currentTarget;
      do {
        sibling = step > 0 ? sibling.nextElementSibling : sibling.previousElementSibling;
      } while (sibling && !(sibling instanceof HTMLElement && sibling.tabIndex === 0));
      if (sibling instanceof HTMLElement) {
        event.preventDefault();
        sibling.focus();
      }
    } else if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
      event.preventDefault();
      props.onToggle(event.key === "ArrowRight");
    } else if (event.key === "Enter") {
      window.location.hash = href({ view: "dossier", fundaId: listing.funda_id });
    } else if (event.key === "x" && !listing.archived) {
      props.onArchive();
    }
  }

  /** A click anywhere on the row folds it open or closed, except on its links and buttons. */
  function handleClick(event: React.MouseEvent<HTMLTableRowElement>) {
    if ((event.target as Element).closest("a, button, input, [role='menu']")) return;
    if (window.getSelection()?.toString()) return;
    props.onToggle(!expanded);
  }

  return (
    <>
      <tr
        tabIndex={0}
        className={classes.filter(Boolean).join(" ") || undefined}
        onKeyDown={handleKey}
        onClick={handleClick}
      >
        <td className="tier-cell">
          <TierMark tier={tierOf(listing)} size="icon" />
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
            {row.stale_count > 0 && (
              <span className="chip stale-chip">
                <Clock size={13} aria-hidden="true" />
                {row.stale_count} verouderd
              </span>
            )}
          </span>
          {row.hard_no_reason && <span className="hard-no-reason">Deal-breaker: {row.hard_no_reason}</span>}
          {props.failure && (
            <span role="alert" className="row-error">
              {props.failure}
            </span>
          )}
        </th>
        <td className="num price-cell" data-label="Vraagprijs">
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
        <td className="signal-counts">
          <SignalCounts counts={row.flag_counts} />
        </td>
        <td className="expand-cell">
          <button
            type="button"
            className="row-expand"
            aria-expanded={expanded}
            aria-controls={detailsId}
            aria-label={expanded ? "Details verbergen" : "Details tonen"}
            onClick={() => props.onToggle(!expanded)}
          >
            <ChevronDown size={18} aria-hidden="true" />
          </button>
        </td>
        <td className="menu-cell">
          <ListingActions
            listing={listing}
            busy={props.busy}
            onRefetch={props.onRefetch}
            onArchive={props.onArchive}
            onRestore={props.onRestore}
            onRerunVerdict={props.onRerunVerdict}
          />
        </td>
      </tr>
      <tr id={detailsId} className="row-details" hidden={!expanded}>
        <td colSpan={6}>
          {expanded && <RowDetails listing={listing} />}
        </td>
      </tr>
    </>
  );
}

function RowDetails({ listing }: { listing: Listing }) {
  const row = listing.comparison;
  return (
    <dl className="row-facts">
      <RowFact
        label="t.o.v. WOZ"
        title="Vraagprijs boven (+) of onder (−) de laatste WOZ-waarde"
        tone={priceTone(row.asking_vs_woz_percent)}
      >
        {signedPercent(row.asking_vs_woz_percent)}
      </RowFact>
      <RowFact
        label="t.o.v. vergelijkbaar"
        title="Vraagprijs per m² boven (+) of onder (−) de mediaan van vergelijkbare woningen"
        tone={priceTone(row.asking_vs_comparables_percent)}
      >
        {signedPercent(row.asking_vs_comparables_percent)}
      </RowFact>
      <RowFact label="Ruimte boven vraag" title="Betaalruimte boven (+) of tekort onder (−) de vraagprijs" tone={headroomTone(row.headroom)}>
        {row.headroom != null ? signedEuro(row.headroom) : "–"}
      </RowFact>
      <RowFact label="Direct nodig" title="Geschatte kosten van direct nodig onderhoud (Verbouwingsraming)">
        {row.renovation_direct
          ? row.renovation_direct.high > 0
            ? euroRange(row.renovation_direct.low, row.renovation_direct.high)
            : "geen"
          : "–"}
      </RowFact>
      <RowFact label="m² woon / perceel">
        {row.living_area ?? "–"} / {row.plot_area ?? "–"}
      </RowFact>
      <RowFact label="Label">
        {row.energy_label ? (
          <>
            <span className={`energy-badge energy-${row.energy_label.value[0].toLowerCase()}`}>{row.energy_label.value}</span>
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
      </RowFact>
      <RowFact label="Opgehaald">{dateTime.format(new Date(row.last_fetched_at))}</RowFact>
    </dl>
  );
}

function RowFact(props: { label: string; title?: string; tone?: string | null; children: ReactNode }) {
  return (
    <div className="row-fact">
      <dt title={props.title}>{props.label}</dt>
      <dd className={`num tone-${props.tone ?? "none"}`}>{props.children}</dd>
    </div>
  );
}

/** Pluspunten, minpunten and risico's as glyph and count; a zero count fades. */
export function SignalCounts({ counts }: { counts: Listing["comparison"]["flag_counts"] }) {
  return (
    <>
      {(["pro", "con", "risk"] as const).map((flagClass) => {
        const count = counts[flagClass];
        const [one, many] = { pro: ["pluspunt", "pluspunten"], con: ["minpunt", "minpunten"], risk: ["risico", "risico's"] }[flagClass];
        return (
          <span key={flagClass} className={`signal-count${count === 0 ? " zero" : ""}`}>
            <FlagGlyph flagClass={flagClass} />
            <span aria-hidden="true">{count}</span>
            <span className="visually-hidden">{plural(count, one, many)}</span>
          </span>
        );
      })}
    </>
  );
}

/** The actions on one Woning, in a row or on a card. */
export function ListingActions(props: {
  listing: Listing;
  busy: boolean;
  onRefetch: (fundaId: string) => void;
  onArchive: () => void;
  onRestore: (fundaId: string) => void;
  onRerunVerdict: (fundaId: string) => void;
}) {
  const { listing } = props;
  return (
    <Menu.Root>
      <Menu.Trigger className="row-menu" aria-label="Acties" disabled={props.busy}>
        <Ellipsis size={18} aria-hidden="true" />
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Positioner className="menu-positioner" align="end">
          <Menu.Popup className="menu">
            <Menu.Item onClick={() => props.onRefetch(listing.funda_id)}>Opnieuw ophalen</Menu.Item>
            <Menu.Item onClick={() => props.onRerunVerdict(listing.funda_id)}>Oordeel opnieuw draaien</Menu.Item>
            {listing.archived ? (
              <Menu.Item onClick={() => props.onRestore(listing.funda_id)}>Terugzetten</Menu.Item>
            ) : (
              <Menu.Item onClick={props.onArchive}>Archiveren</Menu.Item>
            )}
          </Menu.Popup>
        </Menu.Positioner>
      </Menu.Portal>
    </Menu.Root>
  );
}

export function addressOf(listing: Listing): string {
  return listing.snapshots[0].address ?? listing.url;
}

export function statusLabel(status: string, raw: string): string {
  if (status === "available") return "Beschikbaar";
  if (status === "negotiations") return "Onder bod";
  if (status === "sold") return "Verkocht";
  return raw || "Onbekend";
}
