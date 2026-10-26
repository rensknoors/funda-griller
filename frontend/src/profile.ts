export type Role = "adult" | "child";

export type FormState = {
  household: { role: Role; birth_date: string }[];
  gross_annual_income: string;
  savings: string;
  investments: string;
  has_home: boolean;
  home_value: string;
  outstanding_mortgage: string;
  selling_costs: string;
  home_address: string;
  must_haves: string[];
  nice_to_haves: string[];
  deal_breakers: string[];
  commute_destinations: { label: string; address: string; max_minutes: string }[];
  renovation_tolerance: string;
};

export type FieldErrors = Record<string, string>;

export const emptyForm: FormState = {
  household: [{ role: "adult", birth_date: "" }],
  gross_annual_income: "",
  savings: "",
  investments: "",
  has_home: false,
  home_value: "",
  outstanding_mortgage: "",
  selling_costs: "",
  home_address: "",
  must_haves: [],
  nice_to_haves: [],
  deal_breakers: [],
  commute_destinations: [],
  renovation_tolerance: "",
};

// A blank vak is left out of the payload so the API reports it as "Verplicht veld".
const amount = (text: string) => (text.trim() === "" ? undefined : Number(text));

export function toPayload(form: FormState) {
  return {
    household: form.household.map(({ role, birth_date }) => ({ role, birth_date })),
    gross_annual_income: amount(form.gross_annual_income),
    assets: { savings: amount(form.savings), investments: amount(form.investments) },
    current_home: form.has_home
      ? {
          value: amount(form.home_value),
          outstanding_mortgage: amount(form.outstanding_mortgage),
          selling_costs: amount(form.selling_costs),
          address: form.home_address.trim() || null,
        }
      : null,
    must_haves: form.must_haves,
    nice_to_haves: form.nice_to_haves,
    deal_breakers: form.deal_breakers,
    commute_destinations: form.commute_destinations.map((destination) => ({
      label: destination.label,
      address: destination.address,
      max_minutes: amount(destination.max_minutes) ?? null,
    })),
    renovation_tolerance: amount(form.renovation_tolerance),
  };
}

export type SectionId = "huishouden" | "inkomen" | "vermogen" | "wensen" | "reizen";

export const SECTIONS: { id: SectionId; title: string; hint: string; fields: string[] }[] = [
  { id: "huishouden", title: "Huishouden", hint: "Wie er gaat wonen, met geboortedata.", fields: ["household"] },
  { id: "inkomen", title: "Inkomen", hint: "Bruto jaarinkomen van het huishouden.", fields: ["gross_annual_income"] },
  {
    id: "vermogen",
    title: "Vermogen en eigen woning",
    hint: "Spaargeld, beleggingen en de overwaarde van je huidige woning.",
    fields: ["assets", "current_home"],
  },
  {
    id: "wensen",
    title: "Wensen",
    hint: "Must-haves, nice-to-haves en deal-breakers.",
    fields: ["must_haves", "nice_to_haves", "deal_breakers"],
  },
  {
    id: "reizen",
    title: "Reizen en verbouwen",
    hint: "Pendelbestemmingen en hoeveel verbouwing je aankunt.",
    fields: ["commute_destinations", "renovation_tolerance"],
  },
];

export function sectionOf(field: string): SectionId {
  const root = field.split(".")[0];
  return SECTIONS.find((section) => section.fields.includes(root))?.id ?? "huishouden";
}

/** Every vak in page order, so problems are listed and focused top to bottom. */
export function vakOrder(form: FormState): string[] {
  const rows = (prefix: string, count: number, parts: string[] = [""]) =>
    Array.from({ length: count }, (_, i) => parts.map((part) => `${prefix}.${i}${part}`)).flat();
  return [
    ...rows("household", form.household.length, [".role", ".birth_date"]),
    "gross_annual_income",
    "assets.savings",
    "assets.investments",
    ...(form.has_home
      ? ["current_home.value", "current_home.outstanding_mortgage", "current_home.selling_costs", "current_home.address"]
      : []),
    ...rows("must_haves", form.must_haves.length),
    ...rows("nice_to_haves", form.nice_to_haves.length),
    ...rows("deal_breakers", form.deal_breakers.length),
    ...rows("commute_destinations", form.commute_destinations.length, [".label", ".address", ".max_minutes"]),
    "renovation_tolerance",
  ];
}

export const fieldId = (field: string) => `vak-${field.replaceAll(".", "-")}`;

/** The finance vakken the Gevolgen panel needs, or null until income is filled in. */
export function toFinanceDraft(form: FormState) {
  if (form.gross_annual_income.trim() === "") return null;
  const homeFilled = [form.home_value, form.outstanding_mortgage, form.selling_costs].every((text) => text.trim() !== "");
  return {
    household: form.household.filter((member) => member.birth_date !== ""),
    gross_annual_income: amount(form.gross_annual_income),
    assets: { savings: amount(form.savings), investments: amount(form.investments) },
    current_home:
      form.has_home && homeFilled
        ? {
            value: amount(form.home_value),
            outstanding_mortgage: amount(form.outstanding_mortgage),
            selling_costs: amount(form.selling_costs),
          }
        : null,
  };
}

export type Consequences = {
  max_mortgage: number;
  equity: number;
  budget: number;
  rules: { year: number; is_current_year: boolean };
};

type StoredProfile = ReturnType<typeof toPayload>;

export function fromStored(stored: StoredProfile): FormState {
  const text = (value: number | null | undefined) => (value == null ? "" : String(value));
  return {
    household: stored.household,
    gross_annual_income: text(stored.gross_annual_income),
    savings: text(stored.assets.savings),
    investments: text(stored.assets.investments),
    has_home: stored.current_home !== null,
    home_value: text(stored.current_home?.value),
    outstanding_mortgage: text(stored.current_home?.outstanding_mortgage),
    selling_costs: text(stored.current_home?.selling_costs),
    home_address: stored.current_home?.address ?? "",
    must_haves: stored.must_haves,
    nice_to_haves: stored.nice_to_haves,
    deal_breakers: stored.deal_breakers,
    commute_destinations: stored.commute_destinations.map((destination) => ({
      label: destination.label,
      address: destination.address,
      max_minutes: text(destination.max_minutes),
    })),
    renovation_tolerance: text(stored.renovation_tolerance),
  };
}
