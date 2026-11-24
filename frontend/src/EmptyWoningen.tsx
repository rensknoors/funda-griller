import type { CSSProperties } from "react";

import { TierMark } from "./TierMark";
import { href } from "./route";

/** The houses rise into the street one after another. */
const rise = (index: number): CSSProperties => ({ animationDelay: `${80 + index * 90}ms` });

/** Moves the user to the capture field in the hero, the one place a first Woning comes from. */
function focusCapture() {
  const input = document.getElementById("listing-url");
  if (!(input instanceof HTMLInputElement)) return;
  input.scrollIntoView({ block: "center", behavior: "smooth" });
  input.focus({ preventScroll: true });
}

/** A row of Dutch gables with one empty plot. The plot answers the capture field: it lights up
 * while the field has focus and fills in once it holds a link (styles.css, `.straatje`). */
function Straatje() {
  return (
    <svg className="straatje" viewBox="0 0 372 200" aria-hidden="true" focusable="false">
      <line className="straatje-ground" x1="0" y1="190" x2="372" y2="190" />
      {/* Trapgevel */}
      <g className="gevel" style={rise(0)}>
        <path d="M8 190V96h10V80h10V64h10V48h14v16h10v16h10v16h10v94Z" />
        <rect x="22" y="108" width="12" height="16" />
        <rect x="48" y="108" width="12" height="16" />
        <rect x="22" y="140" width="12" height="16" />
        <rect x="48" y="140" width="12" height="16" />
        <rect x="39" y="66" width="8" height="10" />
        <path d="M66 190v-26h-10v26" />
      </g>
      {/* Klokgevel */}
      <g className="gevel" style={rise(1)}>
        <path d="M88 190V104c0-14 12-14 12-28 0-18 8-30 20-30s20 12 20 30c0 14 12 14 12 28v86Z" />
        <rect x="114" y="66" width="12" height="14" rx="6" />
        <rect x="100" y="104" width="12" height="16" />
        <rect x="128" y="104" width="12" height="16" />
        <rect x="100" y="138" width="12" height="16" />
        <path d="M134 190v-30h-12v30" />
      </g>
      {/* The empty plot: the user's first Woning goes here. */}
      <g className="leeg-perceel">
        <path className="leeg-gevel" d="M162 190V82l32-30 32 30v108Z" />
        <path className="leeg-plus" d="M194 112v28M180 126h28" />
        <g className="leeg-ramen">
          <rect x="189" y="70" width="10" height="12" />
          <rect x="172" y="104" width="12" height="16" />
          <rect x="204" y="104" width="12" height="16" />
          <rect x="172" y="138" width="12" height="16" />
          <rect x="204" y="138" width="12" height="16" />
          <path d="M200 190v-28h-12v28" />
        </g>
      </g>
      {/* Halsgevel */}
      <g className="gevel" style={rise(2)}>
        <path d="M236 190v-82h8c0-8 4-12 8-14V62c0-8 6-14 14-16 8 2 14 8 14 16v32c4 2 8 6 8 14h8v82Z" />
        <rect x="260" y="64" width="12" height="16" />
        <rect x="246" y="116" width="12" height="16" />
        <rect x="274" y="116" width="12" height="16" />
        <path d="M272 190v-30h-12v30" />
      </g>
      {/* The G-gevel itself, as the last house in the street. */}
      <g className="gevel gevel-g" style={rise(3)}>
        <path d="M352 104 327 84l-25 20v86h50v-46h-22" />
      </g>
    </svg>
  );
}

/** The Woningen list before the first capture: what happens next, and a street waiting for a house. */
export function EmptyWoningen() {
  return (
    <section className="empty-woningen" aria-labelledby="empty-woningen-title">
      <div className="empty-woningen-text">
        <h2 id="empty-woningen-title">Nog geen woningen</h2>
        <p className="empty-woningen-lede">
          Je straat is nog leeg. Plak een funda-link en de eerste woning schuift ertussen, met een dossier waarin
          elk feit zijn herkomst draagt.
        </p>
        <ol className="empty-timeline">
          <li>
            <strong>Plak een funda-link</strong>
            <span>Van een koopwoning, in het veld hierboven.</span>
            <button type="button" className="link" onClick={focusCapture}>
              Naar het invoerveld
            </button>
          </li>
          <li>
            <strong>Ophalen</strong>
            <span>Advertentie, foto's, registers en documenten komen samen in één dossier.</span>
          </li>
          <li>
            <strong>Oordeel</strong>
            <span>Op jouw verzoek, met biedadvies:</span>
            <span className="empty-tiers">
              <TierMark tier="must_buy" size="compact" />
              <TierMark tier="consider" size="compact" />
              <TierMark tier="skip" size="compact" />
              <TierMark tier="hard_no" size="compact" />
            </span>
          </li>
        </ol>
      </div>
      <Straatje />
      <p className="empty-woningen-foot">
        Vul ook je <a href={href({ view: "koperprofiel" })}>koperprofiel</a> in, dan zie je per woning je
        betaalruimte.
      </p>
    </section>
  );
}
