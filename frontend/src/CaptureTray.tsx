import { Check, LoaderCircle, TriangleAlert, X } from "lucide-react";
import { useEffect, useState } from "react";

import { CAPTURE_STEPS } from "./api";
import { ERROR_COPY, STEP_LABEL, type Capture } from "./captures";
import { href } from "./route";

/** Running and just-finished captures, in a corner of every view, so a capture keeps going (and
 * keeps saying what it does) while the user reads a Dossier or edits the Koperprofiel. */
export function CaptureTray(props: {
  captures: Capture[];
  onDismiss: (id: number) => void;
  onManualEntry: (capture: Capture) => void;
}) {
  const now = useNow(props.captures.some((c) => c.outcome.kind === "running"));
  if (props.captures.length === 0) return null;
  return (
    <section className="capture-tray" aria-label="Ophalen">
      {props.captures.map((capture) => (
        <CaptureCard key={capture.id} capture={capture} now={now} {...props} />
      ))}
    </section>
  );
}

function CaptureCard(props: {
  capture: Capture;
  now: number;
  onDismiss: (id: number) => void;
  onManualEntry: (capture: Capture) => void;
}) {
  const { capture } = props;
  const { outcome } = capture;
  const stepIndex = CAPTURE_STEPS.indexOf(capture.step);
  const dismiss = (
    <button type="button" className="capture-dismiss" aria-label="Sluiten" onClick={() => props.onDismiss(capture.id)}>
      <X size={16} aria-hidden="true" />
    </button>
  );

  if (outcome.kind === "failed") {
    return (
      <div className="capture-card failed" role="alert">
        <TriangleAlert size={18} aria-hidden="true" className="capture-icon" />
        <div className="capture-body">
          <p className="capture-name">{capture.name}</p>
          <p className="capture-step">{ERROR_COPY[outcome.error.kind]}</p>
          {outcome.error.kind === "provider_blocked" && (
            <button type="button" className="small" onClick={() => props.onManualEntry(capture)}>
              Handmatig invoeren
            </button>
          )}
        </div>
        {dismiss}
      </div>
    );
  }

  if (outcome.kind === "done") {
    return (
      <div className="capture-card done" role="status">
        <Check size={18} aria-hidden="true" className="capture-icon" />
        <div className="capture-body">
          <p className="capture-name">{capture.name}</p>
          <p className="capture-step">
            Opgehaald.{" "}
            <a href={href({ view: "dossier", fundaId: outcome.listing.funda_id })} onClick={() => props.onDismiss(capture.id)}>
              Dossier openen
            </a>
          </p>
        </div>
        {dismiss}
      </div>
    );
  }

  const seconds = Math.max(0, Math.floor((props.now - capture.startedAt) / 1000));
  return (
    <div className="capture-card running" role="status" aria-live="polite">
      <LoaderCircle size={18} aria-hidden="true" className="capture-icon spinning" />
      <div className="capture-body">
        <p className="capture-name">{capture.name}</p>
        <p className="capture-step">
          Stap {stepIndex + 1} van {CAPTURE_STEPS.length}: {STEP_LABEL[capture.step]}
          <span className="capture-elapsed" aria-hidden="true">
            {Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, "0")}
          </span>
        </p>
        <ol className="capture-steps" aria-hidden="true">
          {CAPTURE_STEPS.map((step, index) => (
            <li key={step} className={index < stepIndex ? "past" : index === stepIndex ? "current" : undefined} title={STEP_LABEL[step]} />
          ))}
        </ol>
      </div>
    </div>
  );
}

/** The current time, ticking each second while `ticking`; for elapsed times. */
function useNow(ticking: boolean): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!ticking) return;
    setNow(Date.now());
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [ticking]);
  return now;
}
