import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react";
import { type ReactNode, useEffect, useState } from "react";
import { flushSync } from "react-dom";

import {
  type Consequences,
  type FieldErrors,
  type FormState,
  type SectionId,
  SECTIONS,
  emptyForm,
  fieldId,
  fromStored,
  sectionOf,
  toFinanceDraft,
  toPayload,
  vakOrder,
} from "./profile";
import { apiFetch, fetchOutOfDateVerdicts } from "./api";
import { euro } from "./format";
import { href } from "./route";
import { ErrorText, Vak, type VakInputProps } from "./Vak";

type LoadState = { kind: "laden" } | { kind: "fout" } | { kind: "klaar"; form: FormState; firstRun: boolean };

type SaveState =
  | { kind: "idle" }
  | { kind: "saving" }
  /** `changedVerdicts`: Oordelen this save made Achterhaald; null when that count could not be read. */
  | { kind: "saved"; version: number; changedVerdicts: number | null }
  | { kind: "failed" };

type GevolgenState = { kind: "pending" } | { kind: "figures"; data: Consequences } | { kind: "incomplete" };

const TOLERANCE_LABELS = ["Instap-klaar", "Kleine klussen", "Gemiddeld", "Flinke klus", "Project"];
const SHARED_TEXT_NOTE = "Deze tekst gaat mee naar het taalmodel; vul geen adres of postcode in.";
const CHECK_DELAY_MS = 150;


const toFieldErrors = (errors: { field: string; message: string }[]): FieldErrors =>
  Object.fromEntries(errors.map((error) => [error.field, error.message]));

/** Loads the latest Koperprofiel, then hands it to the form; skeleton while loading, banner on failure. */
/** `onSaved` lets the Woningen list refresh: a profile change can change Hard no tiers. */
export function BuyerProfileForm({ onSaved }: { onSaved?: () => void } = {}) {
  const [load, setLoad] = useState<LoadState>({ kind: "laden" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let ignore = false;
    apiFetch("/api/buyer-profile")
      .then(async (response) => {
        if (response.status === 404) return { kind: "klaar", form: emptyForm, firstRun: true } as const;
        if (!response.ok) throw new Error("load failed");
        return { kind: "klaar", form: fromStored((await response.json()).profile), firstRun: false } as const;
      })
      .catch(() => ({ kind: "fout" }) as const)
      .then((next) => !ignore && setLoad(next));
    return () => {
      ignore = true;
    };
  }, [attempt]);

  function retry() {
    setLoad({ kind: "laden" });
    setAttempt((n) => n + 1);
  }

  return (
    <div className="koperprofiel">
      <div className="hero">
        <div className="page-head">
          <h1 id="koperprofiel-title">Koperprofiel</h1>
          <p className="page-lede">Je huishouden, financiën en wensen. Hieruit volgen je betaalruimte en de signalen per woning.</p>
        </div>
      </div>
      {load.kind === "laden" && (
        <div className="skeleton" aria-busy="true">
          <span className="visually-hidden">Koperprofiel laden</span>
          <div className="skeleton-row" />
          <div className="skeleton-row" />
          <div className="skeleton-row" />
          <div className="skeleton-row" />
        </div>
      )}
      {load.kind === "fout" && (
        <div role="alert" className="banner">
          Koperprofiel laden mislukt.{" "}
          <button type="button" onClick={retry}>
            Opnieuw proberen
          </button>
        </div>
      )}
      {load.kind === "klaar" && <ProfileForm initial={load.form} firstRun={load.firstRun} onSaved={onSaved} />}
    </div>
  );
}

function ProfileForm({
  initial,
  firstRun,
  onSaved,
}: {
  initial: FormState;
  firstRun: boolean;
  onSaved?: () => void;
}) {
  const [form, setForm] = useState<FormState>(initial);
  const [touched, setTouched] = useState<ReadonlySet<string>>(new Set());
  const [problems, setProblems] = useState<FieldErrors>({});
  const [save, setSave] = useState<SaveState>({ kind: "idle" });
  const [open, setOpen] = useState<ReadonlySet<SectionId>>(
    new Set(firstRun ? ["huishouden"] : SECTIONS.map((section) => section.id)),
  );
  const gevolgen = useGevolgen(form);

  // Re-check the whole draft whenever a touched vak exists and the input changes.
  useEffect(() => {
    if (touched.size === 0) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      apiFetch("/api/buyer-profile/validation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(form)),
        signal: controller.signal,
      })
        .then((response) => response.json())
        .then((body) => setProblems(toFieldErrors(body.errors)))
        .catch(() => undefined);
    }, CHECK_DELAY_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [form, touched]);

  const order = vakOrder(form);
  const position = (field: string) => {
    const exact = order.indexOf(field);
    return exact >= 0 ? exact : order.findIndex((vak) => vak.startsWith(`${field}.`));
  };
  const isTouched = (field: string) => [...touched].some((t) => t === field || t.startsWith(`${field}.`));
  const visible = Object.keys(problems)
    .filter(isTouched)
    .sort((a, b) => position(a) - position(b));
  const errorOf = (field: string) => (isTouched(field) ? problems[field] : undefined);

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => setForm((current) => ({ ...current, [key]: value }));
  const touch = (fields: string[]) => setTouched((current) => new Set([...current, ...fields]));

  function openSection(id: SectionId) {
    flushSync(() => setOpen((current) => new Set([...current, id])));
  }

  function goToSection(id: SectionId) {
    openSection(id);
    document.getElementById(id)?.querySelector<HTMLElement>("input, select, .section-body button")?.focus();
  }

  function goToField(field: string) {
    const id = sectionOf(field);
    openSection(id);
    const target = document.getElementById(fieldId(field)) ?? document.getElementById(id)?.querySelector<HTMLElement>("input, select");
    target?.focus();
  }

  async function submit() {
    setSave({ kind: "saving" });
    try {
      const response = await apiFetch("/api/buyer-profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(form)),
      });
      if (response.status === 422) {
        const errors = toFieldErrors((await response.json()).errors);
        setProblems(errors);
        touch(Object.keys(errors));
        setOpen((current) => new Set([...current, ...Object.keys(errors).map(sectionOf)]));
        setSave({ kind: "idle" });
      } else if (response.ok) {
        setProblems({});
        setTouched(new Set());
        const { version } = await response.json();
        const changedVerdicts = await fetchOutOfDateVerdicts()
          .then((outOfDate) => outOfDate.count)
          .catch(() => null);
        setSave({ kind: "saved", version, changedVerdicts });
        onSaved?.();
      } else {
        setSave({ kind: "failed" });
      }
    } catch {
      setSave({ kind: "failed" });
    }
  }

  // Inputs carry their field path, so one handler marks any vak as touched on blur.
  const onBlur = (event: React.FocusEvent<HTMLFormElement>) => {
    const field = (event.target as HTMLElement).dataset.field;
    if (field) touch([field]);
  };

  const vak = (field: string, label: string) => ({ field, label, error: errorOf(field) });
  const amountInput = (key: "gross_annual_income" | "savings" | "investments" | "home_value" | "outstanding_mortgage" | "selling_costs") =>
    (props: VakInputProps) => <input {...props} inputMode="numeric" value={form[key]} onChange={(event) => set(key, event.target.value)} />;

  const sectionBody: Record<SectionId, ReactNode> = {
    huishouden: (
      <>
        {errorOf("household") && <ErrorText>{errorOf("household")}</ErrorText>}
        {form.household.map((member, index) => {
          const update = (patch: Partial<typeof member>) =>
            set("household", form.household.map((m, i) => (i === index ? { ...m, ...patch } : m)));
          return (
            <div className="row" key={index}>
              <ProfileVak {...vak(`household.${index}.role`, `Rol lid ${index + 1}`)}>
                {(props) => (
                  <select {...props} value={member.role} onChange={(event) => update({ role: event.target.value as "adult" | "child" })}>
                    <option value="adult">Volwassene</option>
                    <option value="child">Kind</option>
                  </select>
                )}
              </ProfileVak>
              <ProfileVak {...vak(`household.${index}.birth_date`, `Geboortedatum lid ${index + 1}`)}>
                {(props) => <input {...props} type="date" value={member.birth_date} onChange={(event) => update({ birth_date: event.target.value })} />}
              </ProfileVak>
              <button type="button" className="icon-button" aria-label={`Verwijder lid ${index + 1}`} title="Verwijderen" onClick={() => set("household", form.household.filter((_, i) => i !== index))}>
                <Trash2 size={16} aria-hidden="true" />
              </button>
            </div>
          );
        })}
        <button type="button" className="add-button" onClick={() => set("household", [...form.household, { role: "adult", birth_date: "" }])}>
          <Plus size={16} aria-hidden="true" />
          Lid toevoegen
        </button>
      </>
    ),
    inkomen: <ProfileVak {...vak("gross_annual_income", "Bruto jaarinkomen huishouden (€)")}>{amountInput("gross_annual_income")}</ProfileVak>,
    vermogen: (
      <>
        <ProfileVak {...vak("assets.savings", "Spaargeld (€)")}>{amountInput("savings")}</ProfileVak>
        <ProfileVak {...vak("assets.investments", "Beleggingen (€)")}>{amountInput("investments")}</ProfileVak>
        <label className="check">
          <input type="checkbox" checked={form.has_home} onChange={(event) => set("has_home", event.target.checked)} /> Ik heb een eigen woning
        </label>
        {form.has_home && (
          <>
            <ProfileVak {...vak("current_home.value", "Woningwaarde (€)")}>{amountInput("home_value")}</ProfileVak>
            <ProfileVak {...vak("current_home.outstanding_mortgage", "Openstaande hypotheek (€)")}>
              {amountInput("outstanding_mortgage")}
            </ProfileVak>
            <ProfileVak {...vak("current_home.selling_costs", "Verkoopkosten (€)")}>{amountInput("selling_costs")}</ProfileVak>
            <ProfileVak {...vak("current_home.address", "Adres eigen woning (blijft op dit apparaat)")}>
              {(props) => <input {...props} value={form.home_address} onChange={(event) => set("home_address", event.target.value)} />}
            </ProfileVak>
          </>
        )}
      </>
    ),
    wensen: (
      <>
        <p className="hint">{SHARED_TEXT_NOTE}</p>
        {(
          [
            ["must_haves", "Must-have"],
            ["nice_to_haves", "Nice-to-have"],
            ["deal_breakers", "Deal-breaker"],
          ] as const
        ).map(([key, legend]) => (
          <WensList key={key} field={key} legend={legend} rows={form[key]} vak={vak} onChange={(rows) => set(key, rows)} />
        ))}
      </>
    ),
    reizen: (
      <>
        {form.commute_destinations.map((destination, index) => {
          const update = (patch: Partial<typeof destination>) =>
            set("commute_destinations", form.commute_destinations.map((d, i) => (i === index ? { ...d, ...patch } : d)));
          return (
            <div className="commute-destination" key={index} role="group" aria-label={`Pendelbestemming ${index + 1}`}>
              <div className="commute-route">
                <span className="commute-word" aria-hidden="true">Naar</span>
                <ProfileVak {...vak(`commute_destinations.${index}.address`, `Adres van pendelbestemming ${index + 1}`)}>
                  {(props) => <input {...props} value={destination.address} onChange={(event) => update({ address: event.target.value })} />}
                </ProfileVak>
                <span className="commute-word" aria-hidden="true">max.</span>
                <ProfileVak {...vak(`commute_destinations.${index}.max_minutes`, `Maximaal aantal minuten naar pendelbestemming ${index + 1}`)}>
                  {(props) => <input {...props} inputMode="numeric" value={destination.max_minutes} onChange={(event) => update({ max_minutes: event.target.value })} />}
                </ProfileVak>
                <span className="commute-word" aria-hidden="true">min</span>
                <button type="button" className="icon-button" aria-label={`Verwijder pendelbestemming ${index + 1}`} title="Verwijderen" onClick={() => set("commute_destinations", form.commute_destinations.filter((_, i) => i !== index))}>
                  <Trash2 size={16} aria-hidden="true" />
                </button>
              </div>
              <div className="commute-name">
                <ProfileVak {...vak(`commute_destinations.${index}.label`, `Naam van pendelbestemming ${index + 1}`)} hint={SHARED_TEXT_NOTE}>
                  {(props) => <input {...props} value={destination.label} onChange={(event) => update({ label: event.target.value })} />}
                </ProfileVak>
              </div>
            </div>
          );
        })}
        <button type="button" className="add-button" onClick={() => set("commute_destinations", [...form.commute_destinations, { label: "", address: "", max_minutes: "" }])}>
          <Plus size={16} aria-hidden="true" />
          Pendelbestemming toevoegen
        </button>

        <fieldset className="vak" aria-invalid={Boolean(errorOf("renovation_tolerance"))}>
          <legend>
            Verbouwtolerantie
          </legend>
          {TOLERANCE_LABELS.map((label, index) => (
            <label key={label} className="check">
              <input
                type="radio"
                id={index === 0 ? fieldId("renovation_tolerance") : undefined}
                data-field="renovation_tolerance"
                name="renovation_tolerance"
                value={index + 1}
                checked={form.renovation_tolerance === String(index + 1)}
                onChange={() => set("renovation_tolerance", String(index + 1))}
              />{" "}
              {index + 1}. {label}
            </label>
          ))}
          {errorOf("renovation_tolerance") && <ErrorText>{errorOf("renovation_tolerance")}</ErrorText>}
        </fieldset>
      </>
    ),
  };

  const problemCount = visible.length;

  return (
    <form
      className="profile-form"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
      onBlur={onBlur}
      noValidate
      aria-labelledby="koperprofiel-title"
    >
      <nav className="section-index" aria-label="Onderdelen">
        <ol>
          {SECTIONS.map((section) => (
            <li key={section.id}>
              <a
                href={`#${section.id}`}
                onClick={(event) => {
                  event.preventDefault();
                  goToSection(section.id);
                }}
              >
                {section.title}
              </a>
            </li>
          ))}
        </ol>
      </nav>
      <label className="section-select">
        Ga naar onderdeel
        <select value="" onChange={(event) => goToSection(event.target.value as SectionId)}>
          <option value="" disabled>
            Kies een onderdeel
          </option>
          {SECTIONS.map((section) => (
            <option key={section.id} value={section.id}>
              {section.title}
            </option>
          ))}
        </select>
      </label>

      {SECTIONS.map((section) => (
        <section key={section.id} id={section.id} aria-labelledby={`${section.id}-title`} className="form-section">
          <details
            open={open.has(section.id)}
            onToggle={(event) => {
              const isOpen = event.currentTarget.open;
              setOpen((current) => {
                if (current.has(section.id) === isOpen) return current;
                const next = new Set(current);
                if (isOpen) next.add(section.id);
                else next.delete(section.id);
                return next;
              });
            }}
          >
            <summary>
              <h2 id={`${section.id}-title`}>{section.title}</h2>
              <span className="section-hint">{section.hint}</span>
            </summary>
            <div className="section-body">{sectionBody[section.id]}</div>
          </details>
        </section>
      ))}

      <Gevolgen state={gevolgen} />

      <footer className="profile-footer">
        {problemCount > 0 && (
          <p role="status" className="problems">
            
            {problemCount} {problemCount === 1 ? "vak is" : "vakken zijn"} niet correct ingevuld.{" "}
            <a
              href={`#${fieldId(visible[0])}`}
              onClick={(event) => {
                event.preventDefault();
                goToField(visible[0]);
              }}
            >
              Naar het eerste probleem
            </a>
          </p>
        )}
        {save.kind === "saved" && (
          <p role="status">
            Opgeslagen als versie {save.version}.
            {save.changedVerdicts !== null && (
              <>
                {" "}
                {save.changedVerdicts === 0 ? (
                  "Er veranderen geen oordelen."
                ) : (
                  <>
                    Dit verandert {save.changedVerdicts} {save.changedVerdicts === 1 ? "oordeel" : "oordelen"}.
                    Achterhaalde oordelen draaien pas opnieuw als je dat vraagt.{" "}
                    <a href={href({ view: "woningen" })}>Naar de woningen</a>
                  </>
                )}
              </>
            )}
          </p>
        )}
        {save.kind === "failed" && (
          <div role="alert" className="banner">
            Opslaan mislukt. Je invoer is bewaard.{" "}
            <button type="button" onClick={() => void submit()}>
              Opnieuw proberen
            </button>
          </div>
        )}
        <button type="submit" disabled={save.kind === "saving" || problemCount > 0}>
          Opslaan
        </button>
        <p className="muted">Opgeslagen op dit apparaat, nooit geüpload.</p>
      </footer>
    </form>
  );
}

/** Live derived figures for the finance vakken, worked out by the API as the user types. */
function useGevolgen(form: FormState): GevolgenState | null {
  const draft = toFinanceDraft(form);
  const draftKey = JSON.stringify(draft);
  const [state, setState] = useState<GevolgenState>({ kind: "pending" });

  useEffect(() => {
    if (draftKey === "null") return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      apiFetch("/api/buyer-profile/consequences", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: draftKey,
        signal: controller.signal,
      })
        .then(async (response) => setState(response.ok ? { kind: "figures", data: await response.json() } : { kind: "incomplete" }))
        .catch(() => undefined);
    }, CHECK_DELAY_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [draftKey]);

  return draft === null ? null : state;
}

function Gevolgen({ state }: { state: GevolgenState | null }) {
  return (
    <aside className="gevolgen" aria-labelledby="gevolgen-title">
      <details open>
        <summary>
          <h2 id="gevolgen-title">Gevolgen</h2>
        </summary>
        {state === null && <p className="muted">Vul inkomen in om je budget te zien</p>}
        {state?.kind === "pending" && <p className="muted">Gevolgen berekenen…</p>}
        {state?.kind === "incomplete" && <p className="muted">Gevolgen verschijnen zodra de bedragen kloppen.</p>}
        {state?.kind === "figures" && (
          <>
            <dl className="gevolgen-figures">
              <div>
                <dt>Maximale hypotheek</dt>
                <dd className="num">{euro.format(state.data.max_mortgage)}</dd>
              </div>
              <div>
                <dt>Overwaarde</dt>
                <dd className="num">{euro.format(state.data.equity)}</dd>
              </div>
              <div>
                <dt>Budget</dt>
                <dd className="num">{euro.format(state.data.budget)}</dd>
                <dd className="muted note">hoogste koopsom na kosten koper</dd>
              </div>
            </dl>
            <p className="muted rules-year">
              Regels {state.data.rules.year}
              {!state.data.rules.is_current_year && (
                <>
                  {" "}
                  <span className="chip">Achterhaald</span> regels zijn niet van dit jaar
                </>
              )}
            </p>
          </>
        )}
      </details>
    </aside>
  );
}

/** A Koperprofiel vak: its id comes from the field, so jump links and focus can find it. */
function ProfileVak(props: Omit<Parameters<typeof Vak>[0], "id"> & { field: string }) {
  return <Vak {...props} id={fieldId(props.field)} />;
}

/** A repeatable Wensen list: add, remove, and reorder with Alt+↑/↓ or the move buttons. */
function WensList(props: {
  field: "must_haves" | "nice_to_haves" | "deal_breakers";
  legend: string;
  rows: string[];
  vak: (field: string, label: string) => { field: string; label: string; error?: string };
  onChange: (rows: string[]) => void;
}) {
  const { rows, onChange } = props;

  function move(from: number, to: number) {
    if (to < 0 || to >= rows.length) return;
    const next = [...rows];
    [next[from], next[to]] = [next[to], next[from]];
    flushSync(() => onChange(next));
    document.getElementById(fieldId(`${props.field}.${to}`))?.focus();
  }

  return (
    <fieldset>
      <legend>{props.legend}</legend>
      {rows.map((row, index) => {
        const name = `${props.legend} ${index + 1}`;
        return (
          <div className="row" key={index}>
            <ProfileVak {...props.vak(`${props.field}.${index}`, name)}>
              {(input) => (
                <input
                  {...input}
                  aria-keyshortcuts="Alt+ArrowUp Alt+ArrowDown"
                  value={row}
                  onChange={(event) => onChange(rows.map((r, i) => (i === index ? event.target.value : r)))}
                  onKeyDown={(event) => {
                    if (!event.altKey || (event.key !== "ArrowUp" && event.key !== "ArrowDown")) return;
                    event.preventDefault();
                    move(index, event.key === "ArrowUp" ? index - 1 : index + 1);
                  }}
                />
              )}
            </ProfileVak>
            <div className="row-tools">
              <button type="button" className="icon-button" aria-label={`${name} omhoog`} disabled={index === 0} onClick={() => move(index, index - 1)}>
                <ArrowUp size={16} aria-hidden="true" />
              </button>
              <button type="button" className="icon-button" aria-label={`${name} omlaag`} disabled={index === rows.length - 1} onClick={() => move(index, index + 1)}>
                <ArrowDown size={16} aria-hidden="true" />
              </button>
              <button type="button" className="icon-button" aria-label={`Verwijder ${props.legend.toLowerCase()} ${index + 1}`} title="Verwijderen" onClick={() => onChange(rows.filter((_, i) => i !== index))}>
                <Trash2 size={16} aria-hidden="true" />
              </button>
            </div>
          </div>
        );
      })}
      <button type="button" className="add-button" onClick={() => onChange([...rows, ""])}>
        <Plus size={16} aria-hidden="true" />
        {props.legend} toevoegen
      </button>
    </fieldset>
  );
}
