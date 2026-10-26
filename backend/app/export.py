"""Markdown export (Exporteer als Markdown): a house's Case and current Verdict as one Dutch `.md`
file, written for another LLM chat to read. Pure: renders stored data, calls no model.

The reading LLM is unknown and may train on its input, so the Buyer Profile part is always
anonymised (`Anonymiser`): euro amounts derived from the household's finances are rounded (also
where the Verdict's free text names them) and commute destination labels become "Bestemming 1, 2,
…". Without `include_profile` the reduced Buyer Profile and every affordability figure are left
out, and household amounts in the Verdict text read "[weggelaten]". Photos and Documents are never
linked, named or quoted: they are shown only in the app's own UI.

Each section is one function from `ExportInput` to Markdown lines; adding a section is adding one
function to `SECTIONS`.
"""

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from app.buyer_profile import reduce_profile
from app.case import VersionedProfile

# Rounding of euro amounts derived from the household's finances.
AMOUNT_STEP = 5_000
MONTHLY_STEP = 50


@dataclass(frozen=True)
class ExportInput:
    url: str
    snapshot: dict
    case: dict
    # The Listing's Verdict state: `verdicts` newest first, `out_of_date`, `changed`.
    verdicts: dict
    # The latest Buyer Profile; read for destination labels to anonymise even when not included.
    profile: VersionedProfile | None
    include_profile: bool
    now: datetime

    @property
    def with_profile(self) -> bool:
        return self.include_profile and self.profile is not None

    @property
    def verdict(self) -> dict | None:
        history = self.verdicts["verdicts"]
        return history[0] if history else None

    @property
    def anonymiser(self) -> "Anonymiser":
        destinations = self.profile.profile.commute_destinations if self.profile else []
        return Anonymiser(
            {d.label: f"Bestemming {n}" for n, d in enumerate(destinations, start=1)},
            _household_amounts(self),
            self.with_profile,
        )


@dataclass(frozen=True)
class Anonymiser:
    """`destinations` maps a commute destination label to its stand-in. `amounts` are the euro
    amounts that follow from the household's finances, each with its rounding step; in model-written
    text they are rounded when `show_amounts`, else replaced by "[weggelaten]"."""

    destinations: dict[str, str]
    amounts: dict[int, int] = field(default_factory=dict)
    show_amounts: bool = True

    def label(self, label: str) -> str:
        return self.destinations.get(label, label)

    def scrub(self, text: str) -> str:
        """Destination labels in generated text (Flag titles) replaced, longest first."""
        for label in sorted(self.destinations, key=len, reverse=True):
            text = text.replace(label, self.destinations[label])
        return text

    def scrub_text(self, text: str) -> str:
        """Model-written text (Verdict summary, reasoning, conditions): destination labels and the
        known household amounts, in any notation the model may use, replaced. Each match becomes a
        placeholder first, so a replacement is never matched again."""
        text = self.scrub(text)
        replacements: list[str] = []

        def placeholder(amount: int, step: int) -> Callable[[re.Match], str]:
            def replace(_: re.Match) -> str:
                replacements.append(f"≈ {euro(round(amount / step) * step)}" if self.show_amounts else WITHHELD)
                return f"\x00{len(replacements) - 1}\x00"

            return replace

        for amount, step in sorted(self.amounts.items(), reverse=True):
            text = _amount_pattern(amount).sub(placeholder(amount, step), text)
        return re.sub("\x00(\\d+)\x00", lambda m: replacements[int(m[1])], text)


WITHHELD = "[weggelaten]"


def _amount_pattern(amount: int) -> re.Pattern:
    """An amount as "€ 412.345", "€412.345", "412.345", "412,345", "412345" or "€ 412.345,-" and,
    from ten thousand up, "€412k"; never as part of a longer number."""
    dotted = f"{amount:,}".replace(",", ".")
    forms = [re.escape(dotted), re.escape(f"{amount:,}"), str(amount)]
    if amount >= 10_000:
        forms.append(f"{round(amount / 1000)}[kK]\\b")
    return re.compile(rf"(?<![\d.,])(?:€\s?)?(?:{'|'.join(forms)})(?:,-|,00)?(?![\d]|[.,]\d)")


def _household_amounts(export: "ExportInput") -> dict[int, int]:
    """Amounts derived from the household's finances that the Verdict text may name, mapped to
    their rounding step: affordable maximum, home equity, own and available funds, mortgage,
    kosten koper (it reveals starter status), headroom and monthly costs. With the profile the
    exact Maximumbod is shown anyway, so it is left as written; without it, when affordability
    binds, both bids give the affordable maximum away and are left out too."""
    affordability = export.case["affordability"]
    if affordability is None or export.profile is None:
        return {}
    assets = export.profile.profile.assets
    own_funds = assets.savings + assets.investments
    euros = [
        affordability["affordable_maximum"],
        affordability["equity"],
        affordability["max_mortgage"],
        affordability["mortgage_needed"],
        affordability["headroom"],
        (affordability["kosten_koper"] or {}).get("total"),
        assets.savings,
        assets.investments,
        own_funds,
        affordability["equity"] + own_funds,
    ]
    advice = export.verdict["bid_advice"] if export.verdict else None
    monthly = [affordability["monthly_cost"], advice.get("monthly_cost_at_walk_away_maximum") if advice else None]
    amounts = {abs(a): AMOUNT_STEP for a in euros if a} | {abs(a): MONTHLY_STEP for a in monthly if a}
    if export.with_profile and advice:
        amounts.pop(advice["walk_away_maximum"], None)
    elif advice and (advice.get("derivation") or {}).get("binding") == "affordability":
        amounts |= {advice["walk_away_maximum"]: AMOUNT_STEP, advice["opening_bid"]: AMOUNT_STEP}
    return amounts


def filename(export: ExportInput) -> str:
    """`2026-10-26-keizersgracht-12-amsterdam.md`: export date, then address and city."""
    slug = re.sub(r"[^a-z0-9]+", "-", _ascii(_place(export.snapshot) or "").lower()).strip("-")
    return f"{export.now.date().isoformat()}-{slug or export.case['funda_id']}.md"


def render(export: ExportInput) -> str:
    return "\n".join(line for section in SECTIONS for line in [*section(export), ""]).rstrip() + "\n"


# --- Formatting --------------------------------------------------------------------------------


def _place(record: dict) -> str | None:
    """"Keizersgracht 12, Amsterdam" from a record's address and city; None when it has neither."""
    return ", ".join(str(record[key]) for key in ("address", "city") if record.get(key)) or None


def _ascii(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def euro(amount: int | float) -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}€ {abs(round(amount)):,}".replace(",", ".")


def rounded_euro(amount: int | float) -> str:
    """A household-derived amount, rounded to €5.000 and marked as such."""
    return f"≈ {euro(round(amount / AMOUNT_STEP) * AMOUNT_STEP)}"


def rounded_monthly(amount: int | float) -> str:
    return f"≈ {euro(round(amount / MONTHLY_STEP) * MONTHLY_STEP)} per maand"


def _number(value: float) -> str:
    return f"{value:g}".replace(".", ",")


def _percent(value: float) -> str:
    return f"{'+' if value > 0 else ''}{_number(value)}%"


def _yes_no(value: object) -> str:
    return "ja" if value else "nee"


STATUS_LABELS = {"available": "Beschikbaar", "negotiations": "Onder bod", "sold": "Verkocht"}
TIER_LABELS = {
    "must_buy": "Zeker kopen",
    "consider": "Overwegen",
    "skip": "Overslaan",
    "hard_no": "Harde afwijzing",
}
FLAG_CLASSES = {"pro": "Pluspunt", "con": "Minpunt", "risk": "Risico"}
TRUST_LABELS = {"official": "officieel register", "third_party": "derde partij, indicatief"}
CHANGED_LABELS = {
    "case": "het Dossier",
    "buyer_profile": "het Koperprofiel",
    "rules": "de regels",
    "model": "het model",
}
COVERAGE_LABELS = {
    "not_fetched": "niet opgehaald",
    "none": "geen bruikbare vergelijkbare woningen",
    "thin": "Dun (te weinig om op te leunen)",
    "sufficient": "voldoende",
}
FACT_LABELS = {
    "address": "Adres",
    "city": "Plaats",
    "status": "Status",
    "asking_price": "Vraagprijs",
    "living_area": "Woonoppervlak (m²)",
    "plot_area": "Perceeloppervlak (m²)",
    "rooms": "Kamers",
    "bedrooms": "Slaapkamers",
    "construction_year": "Bouwjaar",
    "energy_label": "Energielabel",
    "heating": "Verwarming",
    "ownership_situation": "Eigendomssituatie",
    "woz_value": "WOZ-waarde",
    "flood_depth_m": "Waterdiepte bij overstroming (kleine kans, m)",
    "subsidence_mm_per_year": "Bodemdaling (mm per jaar)",
    "pile_rot_risk_pct": "Risico op paalrot in de buurt (% van de panden)",
    "lden_all_sources_db": "Geluid, alle bronnen (Lden, dB)",
    "lden_road_db": "Geluid, wegverkeer (Lden, dB)",
    "lden_rail_db": "Geluid, treinverkeer (Lden, dB)",
    "lden_air_db": "Geluid, vliegverkeer (Lden, dB)",
    "kitchen_age_years": "Keuken, geschatte leeftijd (jaar)",
    "bathroom_age_years": "Badkamer, geschatte leeftijd (jaar)",
    "damp_or_mould": "Vocht of schimmel zichtbaar",
    "roof_condition": "Staat van het dak",
    "facade_condition": "Staat van de gevel",
    "renovation_needed": "Renovatie nodig",
    "asbestos": "Asbest",
    "leak": "Lekkage",
    "solar_lease": "Zonnepanelen (lease)",
    "erfpacht": "Erfpacht",
    "subsidy": "Subsidie",
    "stays_or_goes": "Blijft of gaat mee",
    "foundation": "Fundering",
    "boiler_old": "Cv-ketel oud",
    "wiring_old": "Elektra oud",
    "other": "Overig",
    "headroom": "Ruimte onder je betaalbare maximum",
    "max_minutes": "Maximale reistijd (min)",
    "threshold": "Drempel",
    "must_haves": "Must-haves",
    "deal_breakers": "Deal-breakers",
    "renovation_tolerance": "Verbouwbereidheid (1-5)",
    "commute_destinations": "Woon-werkbestemmingen",
    "description": "Omschrijving",
    "travel_minutes": "Reistijd (min)",
    "asking_vs_woz": "Vraagprijs gedeeld door WOZ-waarde",
    "must_have": "Must-have",
    "deal_breaker": "Deal-breaker",
    "named_energy_labels": "Genoemde energielabels",
    "renovation_direct_midpoint": "Direct nodig onderhoud (midden)",
}
LEVELS = {
    "good": "goed",
    "fair": "redelijk",
    "poor": "slecht",
    "none": "geen",
    "cosmetic": "cosmetisch",
    "partial": "gedeeltelijk",
    "full": "volledig",
}
MONEY_FACTS = frozenset({"asking_price", "woz_value", "renovation_direct_midpoint"})
MODES = {"car": "auto", "bike": "fiets"}


def _label(key: str) -> str:
    if key.endswith("_mentioned") and key not in FACT_LABELS:
        return f"Genoemd in de advertentie: {key.removesuffix('_mentioned')}"
    return FACT_LABELS.get(key, key)


def _commute_text(travel: dict, anonymiser: Anonymiser) -> str:
    destination = anonymiser.label(travel["destination"])
    if travel.get("minutes") is None:
        reason = "adres niet gevonden" if travel.get("unavailable") == "destination_not_found" else "geen route"
        return f"{destination}: onbekend ({reason})"
    others = ", ".join(
        f"{MODES.get(mode, mode)} {minutes} min"
        for mode, minutes in travel.get("minutes_by_mode", {}).items()
        if mode != travel["mode"]
    )
    rest = f" ({others})" if others else ""
    return f"{destination}: {travel['minutes']} min met de {MODES.get(travel['mode'], travel['mode'])}{rest}, openbaar vervoer niet meegerekend"


def _value(key: str, value: object, anonymiser: Anonymiser) -> str:
    """A fact's value, with commute destination labels anonymised."""
    if isinstance(value, dict) and "destination" in value:
        return _commute_text(value, anonymiser)
    if isinstance(value, list):
        return "; ".join(
            f"{anonymiser.label(v['label'])} (max {v['max_minutes']} min)" if isinstance(v, dict) else str(v)
            for v in value
        ) or "geen"
    return _plain_value(key, value)


def _plain_value(key: str, value: object) -> str:
    """A yes/no, number, amount, status or level, in Dutch."""
    if isinstance(value, bool):
        return _yes_no(value)
    if isinstance(value, (int, float)):
        return euro(value) if key in MONEY_FACTS else _number(value)
    if key == "status" and isinstance(value, str):
        return STATUS_LABELS.get(value, value)
    return LEVELS.get(str(value), str(value))


# --- Sections ----------------------------------------------------------------------------------


def title(export: ExportInput) -> list[str]:
    place = _place(export.snapshot) or export.case["funda_id"]
    notices = [f"> **Let op:** {notice}" for notice in _notices(export)]
    return [f"# Dossier: {place}", *([""] + notices if notices else [])]


def _notices(export: ExportInput) -> list[str]:
    """What the reader must know before trusting anything below, said plainly."""
    verdict, case = export.verdict, export.case
    notices = []
    if verdict is None:
        notices.append("er is nog geen Oordeel voor deze woning; dit bestand bevat alleen het Dossier.")
    elif export.verdicts["out_of_date"]:
        changed = ", ".join(CHANGED_LABELS.get(c, c) for c in export.verdicts["changed"])
        notices.append(
            f"het Oordeel is **Achterhaald**: sindsdien is {changed} veranderd. "
            "Het Oordeel en Biedadvies hieronder gaan over oudere gegevens."
        )
    if (verdict and verdict["tier"] == "hard_no") or case["hard_no"]:
        notices.append("deze woning is een **Harde afwijzing** (Hard no): ze raakt een deal-breaker van het huishouden.")
    return notices


def preamble(export: ExportInput) -> list[str]:
    return [
        "## Over dit bestand",
        "",
        "Dit bestand komt uit **Funda Griller**, een persoonlijk hulpmiddel dat een koopwoning van funda.nl "
        "vastlegt, er een dossier met feiten uit andere bronnen bij verzamelt en één huishouden adviseert of en "
        "hoe het kan bieden. Het is automatisch gemaakt uit opgeslagen gegevens, zonder taalmodel, om als "
        "context in een gesprek met een ander taalmodel te plakken.",
        "",
        "Alle bedragen en kengetallen zijn **beslissingsondersteuning**, geen financieel, juridisch of "
        "bouwkundig advies. Bedragen die uit de financiën van het huishouden volgen zijn afgerond "
        f"(op {euro(AMOUNT_STEP)}, maandlasten op {euro(MONTHLY_STEP)}) en gemarkeerd met ≈. "
        "Woon-werkbestemmingen heten Bestemming 1, 2, …",
        "",
        "### Herkomst van feiten",
        "",
        "Elk feit heeft een herkomst; weeg ze zo:",
        "",
        "- **Advertentie**: gezegd in de funda-advertentie door de verkopende makelaar; niet gecontroleerd.",
        "- **Bron**: uit een externe bron. *Officieel register* is het betrouwbaarst; *derde partij* is indicatief.",
        "- **Waarneming (geschat)**: door een beeldmodel geschat uit de advertentiefoto's; kan fout zijn.",
        "- **Bevinding (door verkoper)**: door de verkoper gezegd in een document, met paginaverwijzing; niet gecontroleerd.",
        "- **Verouderd**: het feit is ouder dan de geldigheidsduur van zijn bron.",
        "- **Berekend**: rekenwerk over andere feiten.",
        "",
        "### Begrippen (Nederlands = Engels)",
        "",
        "- Woning / Advertentie = Listing",
        "- Dossier = Case",
        "- Bron = Source",
        "- Waarneming = Observation",
        "- Bevinding = Finding",
        "- Document = Document",
        "- Signaal = Flag (Pluspunt = pro, Minpunt = con, Risico = risk)",
        "- Vergelijkbare woning = Comparable (Dun = thin)",
        "- Oordeel = Verdict (Zeker kopen = Must buy, Overwegen = Consider, Overslaan = Skip, Harde afwijzing = Hard no)",
        "- Biedadvies = Bid Advice (Openingsbod = opening bid, Maximumbod = Walk-away Maximum, Voorwaarden = conditions)",
        "- Verbouwingsraming = Renovation Estimate (Direct nodig, Binnen 5 jaar, Optioneel)",
        "- Koperprofiel = Buyer Profile",
        "- Verouderd = Stale (een feit); Achterhaald = Out of date (een Oordeel of Dossier)",
    ]


def provenance(export: ExportInput) -> list[str]:
    built = export.case["built_from"]
    verdict = export.verdict
    lines = [
        "## Herkomst van dit dossier",
        "",
        f"- Geëxporteerd op: {export.now.isoformat()}",
        f"- Advertentie vastgelegd op: {export.snapshot.get('fetched_at')} (snapshot {built['snapshot_id']})",
        f"- Versie Koperprofiel: {built['profile_version'] if built['profile_version'] is not None else 'geen'}",
        f"- Versie signaalregels: {built['flag_rules_version']}",
        f"- Versie kostentabel verbouwing: {built['cost_table_version']}",
        f"- Rekenregels betaalbaarheid: {export.case['rules']['year']}",
        f"- Fotoanalyse: {built['observation_run'] if built['observation_run'] is not None else 'geen'}",
        f"- Documenten: {len(built['documents'])}",
    ]
    if verdict:
        model = verdict["built_from"].get("model") or "geen (deterministisch)"
        lines += [
            f"- Oordeel: versie {verdict['version']} van {verdict['created_at']}",
            f"- Model Oordeel: {model}",
            f"- Promptversie Oordeel: {_prompt_version(verdict)}",
        ]
    lines.append(f"- Koperprofiel meegestuurd: {'ja (geanonimiseerd)' if export.with_profile else 'nee'}")
    return lines


def _prompt_version(verdict: dict) -> str:
    """Stored on each model Verdict; older Verdicts did not record it."""
    if verdict.get("deterministic"):
        return "geen (deterministisch)"
    return str(verdict["prompt_version"]) if verdict.get("prompt_version") is not None else "onbekend"


def woning(export: ExportInput) -> list[str]:
    snapshot = export.snapshot
    rows = [
        ("Adres", _place(snapshot)),
        ("Vraagprijs", euro(snapshot["asking_price"]) if snapshot.get("asking_price") is not None else None),
        ("Woonoppervlak", f"{snapshot['living_area']} m²" if snapshot.get("living_area") else None),
        ("Perceeloppervlak", f"{snapshot['plot_area']} m²" if snapshot.get("plot_area") else None),
        ("Bouwjaar", snapshot.get("construction_year")),
        ("Energielabel (advertentie)", snapshot.get("energy_label")),
        ("Status", STATUS_LABELS.get(snapshot.get("status") or "", snapshot.get("raw_status"))),
        ("Vastgelegd op", snapshot.get("fetched_at")),
        ("funda", export.url),
    ]
    lines = ["## Woning", "", *[f"- {name}: {value if value is not None else 'onbekend'}" for name, value in rows]]
    description = snapshot.get("description")
    lines += ["", "### Omschrijving (Advertentie, letterlijk)", ""]
    lines += ["````text", description, "````"] if description else ["Geen omschrijving in de advertentie."]
    return lines


def facts(export: ExportInput) -> list[str]:
    anonymiser = export.anonymiser
    case_facts = export.case["facts"]
    by_class = {p: [f for f in case_facts if f["provenance"] == p] for p in ("listing", "source", "observation", "finding")}
    lines = ["## Feiten", "", "### Advertentie", ""]
    lines += [f"- {_label(f['key'])}: {_value(f['key'], f['value'], anonymiser)}" for f in by_class["listing"]] or ["Geen."]
    lines += ["", "### Bron", ""]
    sourced = [f for f in by_class["source"] if f["source"] not in ("comparables", "commute")]
    lines += [_source_line(f, anonymiser) for f in sourced] or ["Geen."]
    lines += ["", "### Waarneming (geschat)", ""]
    lines += [_observation_line(f) for f in by_class["observation"]] or ["Geen."]
    lines += ["", "### Bevinding (door verkoper)", ""]
    lines += [_finding_line(f) for f in by_class["finding"]] or ["Geen."]
    return lines


def _source_line(fact: dict, anonymiser: Anonymiser) -> str:
    as_of = f", peildatum {fact['as_of']}" if fact.get("as_of") else ""
    stale = " **Verouderd**" if fact.get("stale") else ""
    trust = TRUST_LABELS.get(fact["trust"], fact["trust"])
    return (
        f"- {_label(fact['key'])}: {_value(fact['key'], fact['value'], anonymiser)} "
        f"(Bron: {fact['source']}, {trust}{as_of}, opgehaald {fact['fetched_at']}){stale}"
    )


def _observation_line(fact: dict) -> str:
    note = f" — {fact['note']}" if fact.get("note") else ""
    photos = ", ".join(str(p["number"]) for p in fact.get("photos", []))
    return f"- {_label(fact['key'])}: ≈ {_plain_value(fact['key'], fact['value'])} (geschat, foto {photos}){note}"


def _finding_line(fact: dict) -> str:
    """No quote and no document name: Documents are shown only in the app's own UI."""
    checked = "" if fact.get("verified") else ", tekst niet te controleren (scan)"
    return (
        f"- {_label(fact['key'])} ({'van toepassing' if fact['value'] else 'niet van toepassing'}): "
        f"{fact['statement']} (door verkoper, p. {fact['page']}{checked})."
    )


def metrics(export: ExportInput) -> list[str]:
    case, anonymiser = export.case, export.anonymiser
    lines = ["## Kengetallen", ""]
    woz = case["metrics"]["asking_vs_woz"]
    if woz:
        lines.append(
            f"- Vraagprijs t.o.v. WOZ: {_percent(woz['percent'])} ({euro(woz['asking_price'])} tegen WOZ "
            f"{euro(woz['woz_value'])}, peildatum {woz['woz_as_of']}; WOZ via derde partij)"
        )
    else:
        lines.append("- Vraagprijs t.o.v. WOZ: onbekend")
    vs = case["metrics"]["asking_vs_comparables"]
    detail = (
        f"; {euro(vs['price_per_m2'] or 0)} per m² tegen mediaan {euro(vs['median_price_per_m2'])} per m²"
        if vs["median_price_per_m2"] is not None and vs["price_per_m2"] is not None
        else ""
    )
    percent = _percent(vs["percent"]) if vs["percent"] is not None else "onbekend"
    lines.append(
        f"- Vraagprijs t.o.v. vergelijkbaar: {percent} ({vs['count']} vergelijkbare woningen, "
        f"dekking {COVERAGE_LABELS.get(vs['coverage'], vs['coverage'])}{detail})"
    )
    check = case["metrics"]["energy_label_check"]
    if check:
        lines.append(
            f"- Energielabel advertentie {check['listing']} tegen register {check['register']}: "
            f"{'komt overeen' if check['matches'] else 'komt niet overeen'}"
        )
    lines += _commute_lines(export, anonymiser)
    if export.with_profile and case["affordability"]:
        lines += _affordability_lines(case["affordability"])
    return lines


def _commute_lines(export: ExportInput, anonymiser: Anonymiser) -> list[str]:
    case = export.case
    travel = [f["value"] for f in case["facts"] if f.get("source") == "commute" and f["key"] == "travel_minutes"]
    limits = (
        {d.label: d.max_minutes for d in export.profile.profile.commute_destinations}
        if export.with_profile and export.profile
        else {}
    )
    lines = []
    for value in travel:
        limit = limits.get(value["destination"])
        maximum = f"; maximum {limit} min" if limit else ""
        lines.append(f"- Reistijd naar {_commute_text(value, anonymiser)}{maximum} (Bron: OpenRouteService, derde partij)")
    coverage = case["metrics"]["commute_coverage"]
    if coverage:
        missing = ", ".join(anonymiser.label(label) for label in coverage["not_fetched"])
        lines.append(f"- Reistijd nog niet opgehaald voor: {missing}")
    return lines


def _affordability_lines(affordability: dict) -> list[str]:
    """Every figure here follows from the household's finances: rounded."""
    lines = [
        "- Betaalbaarheid (berekend uit het Koperprofiel, afgerond):",
        f"  - Maximale hypotheek: {rounded_euro(affordability['max_mortgage'])}",
        f"  - Eigen inbreng uit overwaarde: {rounded_euro(affordability['equity'])}",
        f"  - Betaalbaar maximum (koopsom): {rounded_euro(affordability['affordable_maximum'])}"
        + _after_renovation(affordability.get("renovation_direct", 0)),
    ]
    if affordability["headroom"] is not None:
        lines.append(f"  - Ruimte onder het betaalbare maximum bij de vraagprijs: {rounded_euro(affordability['headroom'])}")
    if affordability["mortgage_needed"] is not None:
        lines.append(f"  - Benodigde hypotheek bij de vraagprijs: {rounded_euro(affordability['mortgage_needed'])}")
    if affordability["monthly_cost"] is not None:
        lines.append(f"  - Maandlasten bij de vraagprijs: {rounded_monthly(affordability['monthly_cost'])}")
    if affordability["kosten_koper"]:
        lines.append(f"  - Kosten koper bij de vraagprijs: {rounded_euro(affordability['kosten_koper']['total'])}")
    return lines


def _after_renovation(renovation_direct: int) -> str:
    """The Direct nodig midpoint is a house cost, so it stays exact."""
    return f", na aftrek van {euro(renovation_direct)} Direct nodig (Verbouwingsraming)" if renovation_direct else ""


def comparables(export: ExportInput) -> list[str]:
    listed = [
        f["value"]
        for f in export.case["facts"]
        if f["provenance"] == "source" and f["source"] == "comparables" and f["key"] == "comparable"
    ]
    lines = [
        "## Vergelijkbare woningen",
        "",
        "Door funda naast deze woning aangeboden; de prijs is de (laatste) vraagprijs, geen geregistreerde verkoopprijs.",
        "",
    ]
    return lines + ([_comparable_line(c) for c in listed] or ["Geen opgehaald."])


def _comparable_line(comparable: dict) -> str:
    place = _place(comparable) or "adres onbekend"
    price, area = comparable.get("asking_price"), comparable.get("living_area")
    per_m2 = f", {euro(price / area)} per m²" if price and area else ""
    price_text = euro(price) if price else "prijs onbekend"
    area_text = f"{area} m²" if area else "m² onbekend"
    sold = "verkocht" if comparable.get("recently_sold") else "te koop"
    return f"- {place}: {price_text}, {area_text}{per_m2}, {sold}"


def flags(export: ExportInput) -> list[str]:
    anonymiser = export.anonymiser
    shown = [flag for flag in export.case["flags"] if export.with_profile or not _from_profile(flag)]
    lines = ["## Signalen", ""]
    for flag in shown:
        lines.append(
            f"- **{FLAG_CLASSES.get(flag['class'], flag['class'])}**: {anonymiser.scrub(flag['title'])} "
            f"(regel {flag['rule_id']} v{flag['rule_version']})"
        )
        lines += [f"  - {_evidence(item, anonymiser)}" for item in flag["evidence"]]
    if not shown:
        lines.append("Geen.")
    left_out = len(export.case["flags"]) - len(shown)
    if left_out:
        lines += ["", f"Signalen uit het Koperprofiel weggelaten: {left_out} (Koperprofiel niet meegestuurd)."]
    return lines


def _from_profile(flag: dict) -> bool:
    """A Flag raised from the Buyer Profile (a preference, a commute limit, affordability) carries
    the profile in its title or evidence."""
    return any(item["provenance"] == "buyer_profile" or item["key"] == "headroom" for item in flag["evidence"])


def _evidence(item: dict, anonymiser: Anonymiser) -> str:
    key, value = item["key"], item["value"]
    shown = rounded_euro(value) if key == "headroom" else _value(key, value, anonymiser)
    return f"{_label(key)}: {shown} ({_origin(item)})"


def _origin(item: dict) -> str:
    origin = item["provenance"]
    if origin == "source":
        stale = ", Verouderd" if item.get("stale") else ""
        return f"Bron: {item['source']}, {TRUST_LABELS.get(item['trust'], item['trust'])}{stale}"
    if origin == "finding":
        return f"Bevinding, door verkoper, p. {item['page']}"
    return {
        "listing": "Advertentie",
        "observation": "Waarneming, geschat",
        "computed": "Berekend",
        "buyer_profile": "Koperprofiel",
        "rule": "Regel",
    }.get(origin, origin)


URGENCY_LABELS = {"direct": "Direct nodig", "within_5_years": "Binnen 5 jaar", "optional": "Optioneel"}
MISSING_INPUT_LABELS = {
    "observations": "geen foto-waarnemingen",
    "vragenlijst": "geen Vragenlijst",
    "energielabel": "geen energielabel",
}


def renovation(export: ExportInput) -> list[str]:
    """House costs, the same for every Buyer Profile, so exact. What Direct nodig does to the
    affordable maximum and the Maximumbod lives in the profile part only."""
    estimate = export.case["renovation_estimate"]
    anonymiser = export.anonymiser
    lines = [
        "## Verbouwingsraming",
        "",
        "Wat de woning de komende jaren aan verbouwing kan kosten, per urgentie. Elke post is een **schatting**: "
        "een bandbreedte uit openbare gemiddelde prijzen, alleen opgenomen als een feit uit het Dossier hem "
        f"aanwijst (kostentabel versie {estimate['cost_table_version']}). Geen offerte.",
    ]
    if estimate["missing_inputs"]:
        missing = ", ".join(MISSING_INPUT_LABELS.get(m, m) for m in estimate["missing_inputs"])
        lines += ["", f"Niet meegenomen: {missing}. Posten die daaruit zouden volgen, ontbreken."]
    if not estimate["items"]:
        return [*lines, "", "Geen verbouwingsposten gevonden in de feiten van deze woning."]
    for urgency, label in URGENCY_LABELS.items():
        items = [item for item in estimate["items"] if item["urgency"] == urgency]
        if not items:
            continue
        total = estimate["classes"][urgency]
        midpoint = f" (midden {euro(total['midpoint'])})" if urgency == "direct" else ""
        lines += ["", f"### {label}: {_range(total['low'], total['high'])}{midpoint}", ""]
        for item in items:
            notes = [
                note
                for note, applies in (
                    ("onderzoek op basis van bouwjaar", item["inspection"]),
                    ("woonoppervlak onbekend, middelgrote woning aangenomen", item["size_assumed"]),
                )
                if applies
            ]
            extra = f"; {'; '.join(notes)}" if notes else ""
            lines.append(
                f"- {item['label']}: {_range(item['low'], item['high'])} "
                f"(geschat, prijspeil {item['price_year']}, bron {item['source']}{extra})"
            )
            lines += [f"  - {_evidence(fact, anonymiser)}" for fact in item["evidence"]]
    return lines


def _range(low: int, high: int) -> str:
    return f"{euro(low)} – {euro(high)}"


def verdict(export: ExportInput) -> list[str]:
    current = export.verdict
    lines = ["## Oordeel", ""]
    if current is None:
        return [*lines, "Nog geen Oordeel."]
    if export.verdicts["out_of_date"]:
        lines += ["**Achterhaald**: gemaakt op oudere gegevens dan het Dossier hierboven.", ""]
    lines.append(f"**{TIER_LABELS.get(current['tier'], current['tier'])}** (versie {current['version']}, {current['created_at']})")
    scrub = export.anonymiser.scrub_text
    if current.get("deterministic") and not export.with_profile:
        # Its summary and reasoning name the Deal-breaker, which is Buyer Profile text.
        lines += [
            "",
            "Vastgesteld zonder taalmodel: de woning raakt een Deal-breaker uit het Koperprofiel (niet meegestuurd).",
        ]
    else:
        if current.get("deterministic"):
            lines += ["", f"Vastgesteld zonder taalmodel: de woning raakt deal-breaker ‘{current['deal_breaker']}’."]
        if current.get("summary"):
            lines += ["", scrub(current["summary"])]
        lines += ["", scrub(current["reasoning"])]
    shown_flags = {flag["id"] for flag in export.case["flags"] if export.with_profile or not _from_profile(flag)}
    cited = [f for f in current.get("cited_flags") or [] if f["id"] in shown_flags]
    if cited:
        lines += ["", "Aangehaalde Signalen:"]
        lines += [f"- {FLAG_CLASSES.get(f['class'], f['class'])}: {scrub(f['title'])}" for f in cited]
    return lines


def bid_advice(export: ExportInput) -> list[str]:
    current = export.verdict
    advice = current["bid_advice"] if current else None
    lines = ["## Biedadvies", ""]
    if advice is None:
        return [*lines, "Geen Biedadvies bij dit Oordeel." if current else "Geen Biedadvies: er is nog geen Oordeel."]
    lines += [
        f"- Openingsbod: {_bid(advice, 'opening_bid', export.with_profile)}",
        f"- Maximumbod: {_bid(advice, 'walk_away_maximum', export.with_profile)}",
        "- Voorwaarden:",
        *[f"  - {export.anonymiser.scrub_text(condition)}" for condition in advice["conditions"]],
    ]
    return lines + (_derivation(advice) if export.with_profile else [])


def _bid(advice: dict, key: str, with_profile: bool) -> str:
    """Exact, except without the profile when affordability binds: the Maximumbod is then the
    household's affordable maximum, and the Openingsbod often sits a fixed step below it, so both
    are rounded down."""
    amount = advice[key]
    binding = (advice.get("derivation") or {}).get("binding")
    if with_profile or binding != "affordability":
        return euro(amount)
    return f"{euro(amount // AMOUNT_STEP * AMOUNT_STEP)} (afgerond)"


BASES = {
    "comparables": "wat de vergelijkbare woningen de woning waard maken",
    "asking_price": "de vraagprijs (vergelijkbare woningen dun of ontbrekend)",
    "affordability": "alleen de betaalbaarheid (geen vergelijkbare woningen en geen vraagprijs)",
}


def _derivation(advice: dict) -> list[str]:
    """How the Maximumbod was derived. The exact affordable maximum never appears: when it binds,
    the derivation says so in words."""
    derivation = advice.get("derivation")
    lines = ["", "### Hoe het Maximumbod is berekend", ""]
    if derivation is None:
        return [*lines, "Afleiding niet bewaard bij dit oudere Oordeel."]
    if derivation["basis_maximum"] is not None:
        renovation_direct = derivation.get("renovation_direct") or 0
        less = f", min {euro(renovation_direct)} Direct nodig" if renovation_direct else ""
        lines.append(
            f"- Basis: {BASES[derivation['basis']]}{less}, plus {_number(round(derivation['margin'] * 100, 1))}% "
            f"= {euro(derivation['basis_maximum'])}"
        )
    else:
        lines.append(f"- Basis: {BASES[derivation['basis']]}")
    lines.append(
        "- Het Maximumbod is **begrensd door betaalbaarheid**: wat het huishouden kan betalen ligt lager dan de basis."
        if derivation["binding"] == "affordability"
        else "- Het Maximumbod is begrensd door de basis; de betaalbaarheid ligt hoger."
    )
    if derivation["weakly_grounded"]:
        lines.append("- **Zwak onderbouwd**: niet gebaseerd op voldoende vergelijkbare woningen.")
    if advice.get("monthly_cost_at_walk_away_maximum") is not None:
        lines.append(f"- Maandlasten bij het Maximumbod: {rounded_monthly(advice['monthly_cost_at_walk_away_maximum'])}")
    return lines


def buyer_profile(export: ExportInput) -> list[str]:
    if not export.with_profile or export.profile is None:
        return ["## Koperprofiel", "", "Niet meegestuurd."]
    reduced = reduce_profile(export.profile.version, export.profile.profile)
    anonymiser = export.anonymiser

    def listed(items: list[str]) -> list[str]:
        return [f"  - {item}" for item in items] or ["  - geen"]

    household = reduced["household"]
    destinations = [
        f"  - {anonymiser.label(d['label'])}: maximaal {d['max_minutes']} min" if d["max_minutes"] else f"  - {anonymiser.label(d['label'])}: geen maximum"
        for d in reduced["commute_destinations"]
    ]
    return [
        "## Koperprofiel (geanonimiseerd)",
        "",
        f"- Versie: {reduced['profile_version']}",
        f"- Huishouden: {household['adults']} volwassene(n), {household['children']} kind(eren)",
        f"- Overwaarde huidige woning: {rounded_euro(reduced['home_equity'])}",
        f"- Verbouwbereidheid: {reduced['renovation_tolerance']} van 5",
        "- Must-have:",
        *listed(reduced["must_haves"]),
        "- Nice-to-have:",
        *listed(reduced["nice_to_haves"]),
        "- Deal-breaker:",
        *listed(reduced["deal_breakers"]),
        "- Woon-werkbestemmingen:",
        *(destinations or ["  - geen"]),
    ]


Section = Callable[[ExportInput], list[str]]

SECTIONS: tuple[Section, ...] = (
    title,
    preamble,
    provenance,
    woning,
    facts,
    metrics,
    comparables,
    flags,
    renovation,
    verdict,
    bid_advice,
    buyer_profile,
)
