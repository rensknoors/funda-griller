import { type ReactNode, useId } from "react";

/** One numbered form box: label with vak number, the control, and its error line. */
export function Vak(props: { number: number; label: string; error?: string; children: (ids: { id: string; describedBy?: string; invalid: boolean }) => ReactNode }) {
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <div className="vak">
      <label htmlFor={id}>
        <span className="vak-number">{props.number}</span> {props.label}
      </label>
      {props.children({ id, describedBy: props.error ? errorId : undefined, invalid: Boolean(props.error) })}
      {props.error && (
        <p className="vak-error" id={errorId}>
          <span aria-hidden="true">! </span>
          {props.error}
        </p>
      )}
    </div>
  );
}
