import { Check } from "lucide-react";
import { useEffect, useId, useState } from "react";

import { fetchNote, saveNote } from "./api";

const savedAt = new Intl.DateTimeFormat("nl-NL", { dateStyle: "medium", timeStyle: "short" });

type Load = { kind: "laden" } | { kind: "fout" } | { kind: "klaar"; saved: string; updatedAt: string | null };
type Save = { kind: "rust" } | { kind: "bezig" } | { kind: "bewaard" } | { kind: "fout" };

/** The household's own free text about this Woning (Notitie), under the Woning header on both the
 * Dossier and the Oordeel. Not part of the Dossier: the model reads and weighs it for the Oordeel,
 * and a change makes the Oordeel achterhaald (`onSaved`). */
export function Notitie(props: { fundaId: string; onSaved?: () => void }) {
  const { fundaId, onSaved } = props;
  const [load, setLoad] = useState<Load>({ kind: "laden" });
  const [text, setText] = useState("");
  const [save, setSave] = useState<Save>({ kind: "rust" });
  const fieldId = useId();
  const hintId = useId();

  useEffect(() => {
    let current = true;
    setLoad({ kind: "laden" });
    setSave({ kind: "rust" });
    fetchNote(fundaId)
      .then((note) => {
        if (!current) return;
        setLoad({ kind: "klaar", saved: note.text, updatedAt: note.updated_at });
        setText(note.text);
      })
      .catch(() => current && setLoad({ kind: "fout" }));
    return () => {
      current = false;
    };
  }, [fundaId]);

  const changed = load.kind === "klaar" && text.trim() !== load.saved;

  async function handleSave(event: React.FormEvent) {
    event.preventDefault();
    setSave({ kind: "bezig" });
    try {
      const note = await saveNote(fundaId, text);
      setLoad({ kind: "klaar", saved: note.text, updatedAt: note.updated_at });
      setText(note.text);
      setSave({ kind: "bewaard" });
      onSaved?.();
    } catch {
      setSave({ kind: "fout" });
    }
  }

  return (
    <section className="notitie" aria-labelledby={`${fieldId}-title`}>
      <form onSubmit={handleSave}>
        <h2 id={`${fieldId}-title`} className="notitie-title">
          <label htmlFor={fieldId}>Notitie</label>
        </h2>
        <textarea
          id={fieldId}
          rows={3}
          value={text}
          disabled={load.kind !== "klaar"}
          aria-describedby={hintId}
          placeholder="Wat je zelf weet: van de bezichtiging, de makelaar of de buren."
          onChange={(event) => {
            setText(event.target.value);
            if (save.kind !== "bezig") setSave({ kind: "rust" });
          }}
        />
        <div className="notitie-foot">
          <p id={hintId} className="muted">
            Het model weegt je notitie mee in het oordeel en het biedadvies. Het is geen feit in het
            dossier en geeft geen signalen.
          </p>
          {load.kind === "fout" && (
            <p role="alert" className="notice error">
              Notitie laden mislukt.
            </p>
          )}
          {save.kind === "fout" && (
            <p role="alert" className="notice error">
              Notitie bewaren mislukt. Probeer het opnieuw.
            </p>
          )}
          {save.kind === "bewaard" && !changed && (
            <p role="status" className="notitie-saved">
              <Check size={15} aria-hidden="true" />
              Bewaard
            </p>
          )}
          {save.kind !== "bewaard" && !changed && load.kind === "klaar" && load.updatedAt && (
            <p className="muted notitie-saved">Laatst gewijzigd {savedAt.format(new Date(load.updatedAt))}</p>
          )}
          <button type="submit" disabled={!changed || save.kind === "bezig"}>
            Notitie bewaren
          </button>
        </div>
      </form>
    </section>
  );
}
