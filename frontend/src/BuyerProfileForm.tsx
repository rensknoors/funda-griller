import { useEffect, useState } from "react";

import { Vak } from "./Vak";
import { type FieldErrors, type FormState, emptyForm, fromStored, toPayload } from "./profile";

type SaveState =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "saved"; version: number }
  | { kind: "failed" };

const TOLERANCE_LABELS = ["Instap-klaar", "Kleine klussen", "Gemiddeld", "Flinke klus", "Project"];

function RowList(props: {
  legend: string;
  addLabel: string;
  rows: string[];
  errors: FieldErrors;
  errorPrefix: string;
  onChange: (rows: string[]) => void;
}) {
  return (
    <fieldset>
      <legend>{props.legend}</legend>
      {props.rows.map((row, index) => (
        <div className="row" key={index}>
          <input
            aria-label={`${props.legend} ${index + 1}`}
            aria-invalid={Boolean(props.errors[`${props.errorPrefix}.${index}`])}
            value={row}
            onChange={(event) => props.onChange(props.rows.map((r, i) => (i === index ? event.target.value : r)))}
          />
          <button type="button" onClick={() => props.onChange(props.rows.filter((_, i) => i !== index))}>
            Verwijder {props.legend.toLowerCase()} {index + 1}
          </button>
          {props.errors[`${props.errorPrefix}.${index}`] && (
            <p className="vak-error">! {props.errors[`${props.errorPrefix}.${index}`]}</p>
          )}
        </div>
      ))}
      <button type="button" onClick={() => props.onChange([...props.rows, ""])}>
        {props.addLabel}
      </button>
    </fieldset>
  );
}

export function BuyerProfileForm() {
  const [form, setForm] = useState<FormState>(emptyForm);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [save, setSave] = useState<SaveState>({ kind: "idle" });

  useEffect(() => {
    fetch("/api/buyer-profile")
      .then((response) => (response.ok ? response.json() : null))
      .then((stored) => stored && setForm(fromStored(stored.profile)))
      .catch(() => undefined);
  }, []);

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => setForm((current) => ({ ...current, [key]: value }));

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSave({ kind: "saving" });
    try {
      const response = await fetch("/api/buyer-profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(form)),
      });
      if (response.status === 422) {
        const body: { errors: { field: string; message: string }[] } = await response.json();
        setErrors(Object.fromEntries(body.errors.map((error) => [error.field, error.message])));
        setSave({ kind: "idle" });
      } else if (response.ok) {
        setErrors({});
        setSave({ kind: "saved", version: (await response.json()).version });
      } else {
        setSave({ kind: "failed" });
      }
    } catch {
      setSave({ kind: "failed" });
    }
  }

  const problemCount = Object.keys(errors).length;

  return (
    <form onSubmit={submit} noValidate aria-labelledby="koperprofiel-title">
      <h2 id="koperprofiel-title">Koperprofiel</h2>

      <section aria-labelledby="huishouden">
        <h3 id="huishouden">Huishouden</h3>
        {errors.household && <p className="vak-error">! {errors.household}</p>}
        {form.household.map((member, index) => (
          <div className="row" key={index}>
            <Vak number={1} label={`Rol lid ${index + 1}`}>
              {({ id }) => (
                <select
                  id={id}
                  value={member.role}
                  onChange={(event) =>
                    set("household", form.household.map((m, i) => (i === index ? { ...m, role: event.target.value as "adult" | "child" } : m)))
                  }
                >
                  <option value="adult">Volwassene</option>
                  <option value="child">Kind</option>
                </select>
              )}
            </Vak>
            <Vak number={2} label={`Geboortedatum lid ${index + 1}`} error={errors[`household.${index}.birth_date`]}>
              {({ id, describedBy, invalid }) => (
                <input
                  id={id}
                  type="date"
                  aria-describedby={describedBy}
                  aria-invalid={invalid}
                  value={member.birth_date}
                  onChange={(event) => set("household", form.household.map((m, i) => (i === index ? { ...m, birth_date: event.target.value } : m)))}
                />
              )}
            </Vak>
            <button type="button" onClick={() => set("household", form.household.filter((_, i) => i !== index))}>
              Verwijder lid {index + 1}
            </button>
          </div>
        ))}
        <button type="button" onClick={() => set("household", [...form.household, { role: "adult", birth_date: "" }])}>
          Lid toevoegen
        </button>
      </section>

      <section aria-labelledby="inkomen">
        <h3 id="inkomen">Inkomen</h3>
        <Vak number={3} label="Bruto jaarinkomen huishouden (€)" error={errors.gross_annual_income}>
          {({ id, describedBy, invalid }) => (
            <input id={id} inputMode="numeric" aria-describedby={describedBy} aria-invalid={invalid} value={form.gross_annual_income} onChange={(event) => set("gross_annual_income", event.target.value)} />
          )}
        </Vak>
      </section>

      <section aria-labelledby="vermogen">
        <h3 id="vermogen">Vermogen en eigen woning</h3>
        <Vak number={4} label="Spaargeld (€)" error={errors["assets.savings"]}>
          {({ id, describedBy, invalid }) => (
            <input id={id} inputMode="numeric" aria-describedby={describedBy} aria-invalid={invalid} value={form.savings} onChange={(event) => set("savings", event.target.value)} />
          )}
        </Vak>
        <Vak number={5} label="Beleggingen (€)" error={errors["assets.investments"]}>
          {({ id, describedBy, invalid }) => (
            <input id={id} inputMode="numeric" aria-describedby={describedBy} aria-invalid={invalid} value={form.investments} onChange={(event) => set("investments", event.target.value)} />
          )}
        </Vak>
        <label>
          <input type="checkbox" checked={form.has_home} onChange={(event) => set("has_home", event.target.checked)} /> Ik heb een eigen woning
        </label>
        {form.has_home && (
          <>
            <Vak number={6} label="Woningwaarde (€)" error={errors["current_home.value"]}>
              {({ id, describedBy, invalid }) => (
                <input id={id} inputMode="numeric" aria-describedby={describedBy} aria-invalid={invalid} value={form.home_value} onChange={(event) => set("home_value", event.target.value)} />
              )}
            </Vak>
            <Vak number={7} label="Openstaande hypotheek (€)" error={errors["current_home.outstanding_mortgage"]}>
              {({ id, describedBy, invalid }) => (
                <input id={id} inputMode="numeric" aria-describedby={describedBy} aria-invalid={invalid} value={form.outstanding_mortgage} onChange={(event) => set("outstanding_mortgage", event.target.value)} />
              )}
            </Vak>
            <Vak number={8} label="Verkoopkosten (€)" error={errors["current_home.selling_costs"]}>
              {({ id, describedBy, invalid }) => (
                <input id={id} inputMode="numeric" aria-describedby={describedBy} aria-invalid={invalid} value={form.selling_costs} onChange={(event) => set("selling_costs", event.target.value)} />
              )}
            </Vak>
            <Vak number={9} label="Adres eigen woning (blijft op dit apparaat)">
              {({ id }) => <input id={id} value={form.home_address} onChange={(event) => set("home_address", event.target.value)} />}
            </Vak>
          </>
        )}
      </section>

      <section aria-labelledby="wensen">
        <h3 id="wensen">Wensen</h3>
        <RowList legend="Must-have" addLabel="Must-have toevoegen" rows={form.must_haves} errors={errors} errorPrefix="must_haves" onChange={(rows) => set("must_haves", rows)} />
        <RowList legend="Nice-to-have" addLabel="Nice-to-have toevoegen" rows={form.nice_to_haves} errors={errors} errorPrefix="nice_to_haves" onChange={(rows) => set("nice_to_haves", rows)} />
        <RowList legend="Deal-breaker" addLabel="Deal-breaker toevoegen" rows={form.deal_breakers} errors={errors} errorPrefix="deal_breakers" onChange={(rows) => set("deal_breakers", rows)} />
      </section>

      <section aria-labelledby="reizen">
        <h3 id="reizen">Reizen en verbouwen</h3>
        {form.commute_destinations.map((destination, index) => {
          const update = (patch: Partial<typeof destination>) =>
            set("commute_destinations", form.commute_destinations.map((d, i) => (i === index ? { ...d, ...patch } : d)));
          return (
            <div className="row" key={index}>
              <Vak number={10} label={`Pendelbestemming ${index + 1}: naam`} error={errors[`commute_destinations.${index}.label`]}>
                {({ id, describedBy, invalid }) => <input id={id} aria-describedby={describedBy} aria-invalid={invalid} value={destination.label} onChange={(event) => update({ label: event.target.value })} />}
              </Vak>
              <Vak number={11} label={`Pendelbestemming ${index + 1}: adres`} error={errors[`commute_destinations.${index}.address`]}>
                {({ id, describedBy, invalid }) => <input id={id} aria-describedby={describedBy} aria-invalid={invalid} value={destination.address} onChange={(event) => update({ address: event.target.value })} />}
              </Vak>
              <Vak number={12} label={`Pendelbestemming ${index + 1}: maximaal aantal minuten`} error={errors[`commute_destinations.${index}.max_minutes`]}>
                {({ id, describedBy, invalid }) => <input id={id} inputMode="numeric" aria-describedby={describedBy} aria-invalid={invalid} value={destination.max_minutes} onChange={(event) => update({ max_minutes: event.target.value })} />}
              </Vak>
              <button type="button" onClick={() => set("commute_destinations", form.commute_destinations.filter((_, i) => i !== index))}>
                Verwijder pendelbestemming {index + 1}
              </button>
            </div>
          );
        })}
        <button type="button" onClick={() => set("commute_destinations", [...form.commute_destinations, { label: "", address: "", max_minutes: "" }])}>
          Pendelbestemming toevoegen
        </button>

        <fieldset>
          <legend>
            <span className="vak-number">13</span> Verbouwtolerantie
          </legend>
          {TOLERANCE_LABELS.map((label, index) => (
            <label key={label}>
              <input type="radio" name="renovation_tolerance" value={index + 1} checked={form.renovation_tolerance === String(index + 1)} onChange={() => set("renovation_tolerance", String(index + 1))} /> {index + 1}. {label}
            </label>
          ))}
          {errors.renovation_tolerance && <p className="vak-error">! {errors.renovation_tolerance}</p>}
        </fieldset>
      </section>

      <footer>
        {problemCount > 0 && <p role="alert">{problemCount} {problemCount === 1 ? "vak is" : "vakken zijn"} niet correct ingevuld.</p>}
        {save.kind === "saved" && <p role="status">Opgeslagen als versie {save.version}.</p>}
        {save.kind === "failed" && <p role="alert">Opslaan mislukt. Je invoer is bewaard; probeer het opnieuw.</p>}
        <button type="submit" disabled={save.kind === "saving"}>Opslaan</button>
        <p>Opgeslagen op dit apparaat, nooit geüpload.</p>
      </footer>
    </form>
  );
}
