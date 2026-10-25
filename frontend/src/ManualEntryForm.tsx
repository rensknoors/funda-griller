import { useState } from "react";

import { type Listing, enterListing } from "./api";
import { Vak } from "./Vak";

type Submit = { kind: "idle" } | { kind: "saving" } | { kind: "failed" };

const STATUSES = ["Beschikbaar", "Onder bod", "Verkocht"];
const ENERGY_LABELS = ["A++++", "A+++", "A++", "A+", "A", "B", "C", "D", "E", "F", "G"];

const NUMBER_FIELDS: [name: string, label: string][] = [
  ["asking_price", "Vraagprijs (€)"],
  ["living_area", "Woonoppervlak (m²)"],
  ["plot_area", "Perceeloppervlak (m²)"],
  ["rooms", "Kamers"],
  ["bedrooms", "Slaapkamers"],
  ["construction_year", "Bouwjaar"],
];

/** Fallback for when the fetch provider is blocked: the user types the advertentie in. */
export function ManualEntryForm(props: {
  url: string;
  onSaved: (listing: Listing) => void;
  onDuplicate: (fundaId: string) => void;
  onCancel: () => void;
}) {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submit, setSubmit] = useState<Submit>({ kind: "idle" });

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmit({ kind: "saving" });
    setErrors({});
    const result = await enterListing(new FormData(event.currentTarget));
    if (!("kind" in result)) {
      props.onSaved(result);
      return;
    }
    setSubmit({ kind: "idle" });
    if (result.kind === "already_captured") props.onDuplicate(result.fundaId);
    else if (result.kind === "bad_url") setErrors({ url: "Ongeldige URL. Gebruik een funda-link van een koopwoning." });
    else if (result.kind === "not_an_image") setErrors({ photos: "Alleen afbeeldingen (jpg, png, …) zijn toegestaan." });
    else if (result.kind === "invalid") setErrors(result.errors);
    else setSubmit({ kind: "failed" });
  }

  const problemCount = Object.keys(errors).length;
  let number = 0;
  const next = () => ++number;

  return (
    <form className="manual-entry" aria-label="Woning handmatig invoeren" onSubmit={handleSubmit} noValidate>
      <h3>Woning handmatig invoeren</h3>
      <p className="muted">
        Neem de gegevens over uit de advertentie. Het dossier wordt er net zo uit opgebouwd als uit een opgehaalde
        advertentie. Foto's worden alleen lokaal bewaard.
      </p>
      <div className="manual-grid">
        <Vak number={next()} label="Funda-link" error={errors.url}>
          {({ id, describedBy, invalid }) => (
            <input id={id} name="url" type="url" required defaultValue={props.url} aria-describedby={describedBy} aria-invalid={invalid} />
          )}
        </Vak>
        <Vak number={next()} label="Status" error={errors.raw_status}>
          {({ id, describedBy, invalid }) => (
            <select id={id} name="raw_status" required defaultValue="Beschikbaar" aria-describedby={describedBy} aria-invalid={invalid}>
              {STATUSES.map((status) => (
                <option key={status}>{status}</option>
              ))}
            </select>
          )}
        </Vak>
        <Vak number={next()} label="Adres" error={errors.address}>
          {({ id, describedBy, invalid }) => <input id={id} name="address" aria-describedby={describedBy} aria-invalid={invalid} />}
        </Vak>
        <Vak number={next()} label="Plaats" error={errors.city}>
          {({ id, describedBy, invalid }) => <input id={id} name="city" aria-describedby={describedBy} aria-invalid={invalid} />}
        </Vak>
        {NUMBER_FIELDS.map(([name, label]) => (
          <Vak key={name} number={next()} label={label} error={errors[name]}>
            {({ id, describedBy, invalid }) => (
              <input id={id} name={name} inputMode="numeric" aria-describedby={describedBy} aria-invalid={invalid} />
            )}
          </Vak>
        ))}
        <Vak number={next()} label="Energielabel" error={errors.energy_label}>
          {({ id, describedBy, invalid }) => (
            <select id={id} name="energy_label" defaultValue="" aria-describedby={describedBy} aria-invalid={invalid}>
              <option value="">Onbekend</option>
              {ENERGY_LABELS.map((label) => (
                <option key={label}>{label}</option>
              ))}
            </select>
          )}
        </Vak>
        <Vak number={next()} label="Verwarming" error={errors.heating}>
          {({ id, describedBy, invalid }) => <input id={id} name="heating" aria-describedby={describedBy} aria-invalid={invalid} />}
        </Vak>
        <Vak number={next()} label="Eigendomssituatie" error={errors.ownership_situation}>
          {({ id, describedBy, invalid }) => (
            <input id={id} name="ownership_situation" placeholder="Volle eigendom" aria-describedby={describedBy} aria-invalid={invalid} />
          )}
        </Vak>
      </div>
      <Vak number={next()} label="Omschrijving" error={errors.description}>
        {({ id, describedBy, invalid }) => <textarea id={id} name="description" rows={4} aria-describedby={describedBy} aria-invalid={invalid} />}
      </Vak>
      <Vak number={next()} label="Foto's" error={errors.photos}>
        {({ id, describedBy, invalid }) => (
          <input id={id} name="photos" type="file" accept="image/*" multiple aria-describedby={describedBy} aria-invalid={invalid} />
        )}
      </Vak>
      <footer>
        {problemCount > 0 && (
          <p role="alert">
            {problemCount} {problemCount === 1 ? "vak is" : "vakken zijn"} niet correct ingevuld.
          </p>
        )}
        {submit.kind === "failed" && <p role="alert">Opslaan mislukt. Je invoer is bewaard; probeer het opnieuw.</p>}
        <div className="row">
          <button type="submit" disabled={submit.kind === "saving"}>
            Woning opslaan
          </button>
          <button type="button" onClick={props.onCancel}>
            Annuleren
          </button>
        </div>
      </footer>
    </form>
  );
}
