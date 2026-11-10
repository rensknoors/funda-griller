import type { Rules } from "./api";

export type Role = "adult" | "child";

export type DebtKind = "study_loan" | "revolving_credit" | "instalment_loan" | "private_lease" | "other";
export type Stelsel = "SF35" | "SF15";

/** One debt as typed: every kind's vakken, of which only the chosen kind's are sent. */
export type DebtRow = {
  kind: DebtKind;
  debt: string;
  /** In percent, as on Mijn DUO ("2,57"). */
  interest_rate: string;
  stelsel: Stelsel;
  monthly_override: string;
  limit: string;
  monthly_term: string;
  monthly: string;
};

export const DEBT_KINDS: { kind: DebtKind; label: string; hint: string }[] = [
  {
    kind: "study_loan",
    label: "Studieschuld",
    hint: "Op Mijn DUO: de schuld bij de start van het terugbetalen (nog studerend: de schuld nu), de rente en je terugbetaalregels. De bank rekent met het wettelijk maandbedrag, ook in de aanloopfase.",
  },
  {
    kind: "revolving_credit",
    label: "Doorlopend krediet",
    hint: "Ook creditcard. De kredietlimiet uit je contract of BKR-overzicht; telt mee als je niets hebt opgenomen.",
  },
  { kind: "instalment_loan", label: "Aflopend krediet", hint: "Autolening of persoonlijke lening: het maandbedrag uit je contract of BKR-overzicht." },
  { kind: "private_lease", label: "Private lease", hint: "Het maandbedrag uit je leasecontract." },
  { kind: "other", label: "Andere lening", hint: "Het maandbedrag." },
];

export const debtLabel = (kind: string) => DEBT_KINDS.find((entry) => entry.kind === kind)?.label ?? kind;

export const emptyDebt = (kind: DebtKind): DebtRow => ({
  kind,
  debt: "",
  interest_rate: "",
  stelsel: "SF35",
  monthly_override: "",
  limit: "",
  monthly_term: "",
  monthly: "",
});

/** The vakken a kind of debt asks for, in form order. */
export const DEBT_FIELDS: Record<DebtKind, (keyof DebtRow)[]> = {
  study_loan: ["debt", "interest_rate", "stelsel", "monthly_override"],
  revolving_credit: ["limit"],
  instalment_loan: ["monthly_term"],
  private_lease: ["monthly_term"],
  other: ["monthly"],
};

export type FormState = {
  household: { role: Role; birth_date: string; starter_exemption_used: boolean }[];
  gross_annual_income: string;
  fixed_rate_years: string;
  /** Own offered rates in percent as typed ("4,25"); blank: the market rate applies. */
  offered_rate_nhg: string;
  offered_rate_no_nhg: string;
  debts: DebtRow[];
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
  household: [{ role: "adult", birth_date: "", starter_exemption_used: false }],
  gross_annual_income: "",
  fixed_rate_years: "10",
  offered_rate_nhg: "",
  offered_rate_no_nhg: "",
  debts: [],
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
/** A percentage typed with a comma or a point, as a fraction: "2,57" is 0.0257. */
const debtRate = (text: string) => (text.trim() === "" ? undefined : Number((Number(text.replace(",", ".")) / 100).toFixed(6)));

function debtPayload(row: DebtRow) {
  switch (row.kind) {
    case "study_loan":
      return {
        kind: row.kind,
        debt: amount(row.debt),
        interest_rate: debtRate(row.interest_rate),
        stelsel: row.stelsel,
        monthly_override: amount(row.monthly_override) ?? null,
      };
    case "revolving_credit":
      return { kind: row.kind, limit: amount(row.limit) };
    case "instalment_loan":
    case "private_lease":
      return { kind: row.kind, monthly_term: amount(row.monthly_term) };
    case "other":
      return { kind: row.kind, monthly: amount(row.monthly) };
  }
}

/** A percentage as typed ("4,25" or "4.25") as the fraction the API takes; blank is null. Text that
 * is no number goes as typed, so the API names the vak. */
function rate(text: string): number | string | null {
  const typed = text.trim();
  if (typed === "") return null;
  const percent = Number(typed.replace(",", "."));
  return Number.isFinite(percent) ? Number((percent / 100).toFixed(6)) : typed;
}

/** A stored fraction back as a Dutch percentage: 0.0425 → "4,25". */
const percentText = (fraction: number | null | undefined) =>
  fraction == null ? "" : String(Number((fraction * 100).toFixed(4))).replace(".", ",");

export function toPayload(form: FormState) {
  return {
    household: form.household.map(({ role, birth_date, starter_exemption_used }) => ({
      role,
      birth_date,
      starter_exemption_used,
    })),
    gross_annual_income: amount(form.gross_annual_income),
    fixed_rate_years: amount(form.fixed_rate_years),
    offered_rate_nhg: rate(form.offered_rate_nhg),
    offered_rate_no_nhg: rate(form.offered_rate_no_nhg),
    debts: form.debts.map(debtPayload),
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
  {
    id: "inkomen",
    title: "Inkomen en lasten",
    hint: "Bruto jaarinkomen, rentevaste periode, aangeboden rente en schulden.",
    fields: ["gross_annual_income", "fixed_rate_years", "offered_rate_nhg", "offered_rate_no_nhg", "debts"],
  },
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
    "fixed_rate_years",
    "offered_rate_nhg",
    "offered_rate_no_nhg",
    ...form.debts.flatMap((row, i) => [`debts.${i}.kind`, ...DEBT_FIELDS[row.kind].map((key) => `debts.${i}.${key}`)]),
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
    // A half-typed period falls back to the default rather than blanking the panel.
    fixed_rate_years: amount(form.fixed_rate_years) ?? 10,
    offered_rate_nhg: rate(form.offered_rate_nhg),
    offered_rate_no_nhg: rate(form.offered_rate_no_nhg),
    // A half-typed debt is left out rather than blanking the panel.
    debts: form.debts.filter((row) => DEBT_FIELDS[row.kind].every((key) => key === "monthly_override" || String(row[key]).trim() !== "")).map(debtPayload),
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

/** One debt's toetslast (per month, before the gross-up) and the leenruimte it costs. */
export type DebtCost = { kind: DebtKind; toetslast: number; costs: number };

export type Consequences = {
  max_mortgage: number;
  equity: number;
  budget: number;
  debts: DebtCost[];
  rules: Rules;
};

type StoredProfile = ReturnType<typeof toPayload>;
type StoredDebt = StoredProfile["debts"][number];

function fromStoredDebt(stored: StoredDebt): DebtRow {
  const text = (value: number | null | undefined) => (value == null ? "" : String(value));
  const row = emptyDebt(stored.kind);
  switch (stored.kind) {
    case "study_loan":
      return {
        ...row,
        debt: text(stored.debt),
        interest_rate: stored.interest_rate == null ? "" : String(Number((stored.interest_rate * 100).toFixed(4))).replace(".", ","),
        stelsel: stored.stelsel,
        monthly_override: text(stored.monthly_override),
      };
    case "revolving_credit":
      return { ...row, limit: text(stored.limit) };
    case "instalment_loan":
    case "private_lease":
      return { ...row, monthly_term: text(stored.monthly_term) };
    case "other":
      return { ...row, monthly: text(stored.monthly) };
  }
}

export function fromStored(stored: StoredProfile): FormState {
  const text = (value: number | null | undefined) => (value == null ? "" : String(value));
  return {
    household: stored.household.map((member) => ({
      ...member,
      starter_exemption_used: member.starter_exemption_used ?? false,
    })),
    gross_annual_income: text(stored.gross_annual_income),
    fixed_rate_years: text(stored.fixed_rate_years ?? 10),
    offered_rate_nhg: percentText(stored.offered_rate_nhg as number | null | undefined),
    offered_rate_no_nhg: percentText(stored.offered_rate_no_nhg as number | null | undefined),
    debts: (stored.debts ?? []).map(fromStoredDebt),
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
