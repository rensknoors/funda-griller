/** Small figure graphics, drawn in HTML so they scale with the text. Each one repeats its figures
 * in a visually hidden list, so a screen reader hears the numbers, not the drawing. */

import { euro, euroRange } from "./format";

export type ScaleMarker = {
  label: string;
  value: number;
  /** The figure the others are read against: a dot above the line instead of a tick below it. */
  primary?: boolean;
  tone?: "favorable" | "concern" | "shortfall";
};

/** Fraction of the scale two labels need between them before the second drops a row. */
const LABEL_GAP = 0.16;

/** Euro figures on one line, so their distance reads at a glance. `span` shades the stretch
 * between two of them, e.g. the room between asking price and the buyer's maximum. */
export function PriceScale(props: {
  label: string;
  markers: ScaleMarker[];
  span?: { from: number; to: number; label: string; tone: "favorable" | "shortfall" | "neutral" };
}) {
  const values = props.markers.map((m) => m.value);
  if (props.span) values.push(props.span.from, props.span.to);
  const low = Math.min(...values);
  const high = Math.max(...values);
  const pad = (high - low || high * 0.1) * 0.08;
  const min = low - pad;
  const max = high + pad;
  const at = (value: number) => (value - min) / (max - min);

  const references = props.markers.filter((m) => !m.primary).sort((a, b) => a.value - b.value);
  const rows: number[] = [];
  const placed = references.map((marker) => {
    const position = at(marker.value);
    let row = rows.findIndex((last) => position - last >= LABEL_GAP);
    if (row === -1) row = rows.length;
    rows[row] = position;
    return { marker, position, row };
  });
  const primary = props.markers.filter((m) => m.primary);

  return (
    <figure className="price-scale">
      <figcaption className="visually-hidden">
        {props.label}:{" "}
        {props.markers.map((m) => `${m.label} ${euro.format(m.value)}`).join(", ")}
        {props.span && `; ${props.span.label}`}
      </figcaption>
      <div className="price-scale-graphic" aria-hidden="true" style={{ paddingBottom: `${Math.max(1, rows.length) * 38}px` }}>
        {primary.map((marker) => (
          <span key={marker.label} className="scale-primary" style={{ left: `${at(marker.value) * 100}%` }}>
            <span className="scale-primary-label">{marker.label}</span>
            <strong className="num">{euro.format(marker.value)}</strong>
          </span>
        ))}
        <span className="scale-track">
          {props.span && (
            <span
              className={`scale-span span-${props.span.tone}`}
              style={{
                left: `${at(Math.min(props.span.from, props.span.to)) * 100}%`,
                width: `${Math.abs(at(props.span.to) - at(props.span.from)) * 100}%`,
              }}
            />
          )}
          {primary.map((marker) => (
            <span key={marker.label} className="scale-dot" style={{ left: `${at(marker.value) * 100}%` }} />
          ))}
          {placed.map(({ marker, position }) => (
            <span key={marker.label} className="scale-tick" style={{ left: `${position * 100}%` }} />
          ))}
        </span>
        {placed.map(({ marker, position, row }) => (
          <span
            key={marker.label}
            className={`scale-reference tone-${marker.tone ?? "none"}${position > 0.8 ? " end" : position < 0.2 ? " start" : ""}`}
            style={{ left: `${position * 100}%`, top: `${54 + row * 38}px` }}
          >
            <span className="scale-reference-label">{marker.label}</span>
            <span className="num">{euro.format(marker.value)}</span>
          </span>
        ))}
      </div>
    </figure>
  );
}

export type BarSegment = { label: string; value: number; kind: "price" | "tax" | "fees" | "renovation" };

/** Parts of one total side by side in a single bar, with a legend of their amounts. */
export function StackedBar(props: { label: string; total: string; segments: BarSegment[] }) {
  const segments = props.segments.filter((s) => s.value > 0);
  const sum = segments.reduce((total, s) => total + s.value, 0);
  if (sum === 0) return null;
  return (
    <figure className="stacked-bar">
      <figcaption>
        <span>{props.label}</span>
        <strong className="num">{props.total}</strong>
      </figcaption>
      <div className="stacked-bar-track" aria-hidden="true">
        {segments.map((segment) => (
          <span
            key={segment.label}
            className={`bar-segment segment-${segment.kind}`}
            style={{ flexGrow: segment.value }}
            title={`${segment.label}: ${euro.format(segment.value)}`}
          />
        ))}
      </div>
      <ul className="bar-legend">
        {segments.map((segment) => (
          <li key={segment.label}>
            <span className={`legend-swatch segment-${segment.kind}`} aria-hidden="true" />
            {segment.label} <span className="num">{euro.format(segment.value)}</span>
          </li>
        ))}
      </ul>
    </figure>
  );
}

export type RangeRow = { label: string; low: number; high: number; tone: "vermilion" | "ochre" | "ink" };

/** Low-to-high ranges on one shared scale from zero, so the classes compare by length. */
export function RangeBars(props: { label: string; rows: RangeRow[] }) {
  const rows = props.rows.filter((r) => r.high > 0);
  const max = Math.max(...rows.map((r) => r.high), 0);
  if (max === 0) return null;
  return (
    <figure className="range-bars">
      <figcaption className="visually-hidden">{props.label}</figcaption>
      {rows.map((row) => (
        <div key={row.label} className="range-row">
          <span className="range-label">{row.label}</span>
          <span className="range-track" aria-hidden="true">
            <span className={`range-fill range-${row.tone}`} style={{ left: `${(row.low / max) * 100}%`, width: `${Math.max(((row.high - row.low) / max) * 100, 1.5)}%` }} />
            <span className={`range-solid range-${row.tone}`} style={{ width: `${(row.low / max) * 100}%` }} />
          </span>
          <span className="range-value num">{euroRange(row.low, row.high)}</span>
        </div>
      ))}
    </figure>
  );
}
