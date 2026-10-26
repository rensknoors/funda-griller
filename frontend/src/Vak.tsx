import { type ReactNode, useId } from "react";

/** What a Vak hands its control: spread it onto the input, select or textarea. */
export type VakInputProps = {
  id: string;
  "data-field"?: string;
  "aria-describedby"?: string;
  "aria-invalid": boolean;
};

/** One labelled form field: the label, the control, an optional hint, and its error line.
 * `field` names the form field (for jump links and focus); `id` overrides the generated id. */
export function Vak(props: {
  label: string;
  error?: string;
  hint?: string;
  field?: string;
  id?: string;
  children: (input: VakInputProps) => ReactNode;
}) {
  const generated = useId();
  const id = props.id ?? generated;
  const describedBy = [props.error && `${id}-error`, props.hint && `${id}-hint`].filter(Boolean).join(" ") || undefined;
  return (
    <div className="vak" data-invalid={props.error ? "" : undefined}>
      <div className="vak-head">
        <label htmlFor={id}>{props.label}</label>
      </div>
      {props.children({ id, "data-field": props.field, "aria-describedby": describedBy, "aria-invalid": Boolean(props.error) })}
      {props.hint && (
        <p className="hint" id={`${id}-hint`}>
          {props.hint}
        </p>
      )}
      {props.error && <ErrorText id={`${id}-error`}>{props.error}</ErrorText>}
    </div>
  );
}

export function ErrorText({ id, children }: { id?: string; children: ReactNode }) {
  return (
    <p className="vak-error" id={id}>
      
      {children}
    </p>
  );
}
