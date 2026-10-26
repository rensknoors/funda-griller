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

  return (
    <form className="manual-entry" aria-label="Woning handmatig invoeren" onSubmit={handleSubmit} noValidate>
      <h2>Woning handmatig invoeren</h2>
      <p className="muted">
        Neem de gegevens over uit de advertentie. Het dossier wordt er net zo uit opgebouwd als uit een opgehaalde
        advertentie. Foto's worden alleen lokaal bewaard.
      </p>
      <div className="manual-grid">
        <Vak label="Funda-link" error={errors.url}>
          {(input) => (
            <input {...input} name="url" type="url" required defaultValue={props.url} />
          )}
        </Vak>
        <Vak label="Status" error={errors.raw_status}>
          {(input) => (
            <select {...input} name="raw_status" required defaultValue="Beschikbaar">
              {STATUSES.map((status) => (
                <option key={status}>{status}</option>
              ))}
            </select>
          )}
        </Vak>
        <Vak label="Adres" error={errors.address}>
          {(input) => <input {...input} name="address" />}
        </Vak>
        <Vak label="Plaats" error={errors.city}>
          {(input) => <input {...input} name="city" />}
        </Vak>
        {NUMBER_FIELDS.map(([name, label]) => (
          <Vak key={name} label={label} error={errors[name]}>
            {(input) => (
              <input {...input} name={name} inputMode="numeric" />
            )}
          </Vak>
        ))}
        <Vak label="Energielabel" error={errors.energy_label}>
          {(input) => (
            <select {...input} name="energy_label" defaultValue="">
              <option value="">Onbekend</option>
              {ENERGY_LABELS.map((label) => (
                <option key={label}>{label}</option>
              ))}
            </select>
          )}
        </Vak>
        <Vak label="Verwarming" error={errors.heating}>
          {(input) => <input {...input} name="heating" />}
        </Vak>
        <Vak label="Eigendomssituatie" error={errors.ownership_situation}>
          {(input) => (
            <input {...input} name="ownership_situation" placeholder="Volle eigendom" />
          )}
        </Vak>
      </div>
      <Vak label="Omschrijving" error={errors.description}>
        {(input) => <textarea {...input} name="description" rows={4} />}
      </Vak>
      <Vak label="Foto's" error={errors.photos}>
        {(input) => (
          <input {...input} name="photos" type="file" accept="image/*" multiple />
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
