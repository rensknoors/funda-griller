"""Affordability engine: pure arithmetic over a Buyer Profile, an asking price and one year's rules.

The maximum mortgage follows the Tijdelijke regeling hypothecair krediet: a financieringslast-
percentage by toetsinkomen and toetsrente, turned into a mortgage with a 30-year annuity at that
rate. A rentevaste periode under ten years tests at the AFM toetsrente (or the offered rate when
higher); ten years or longer at the offered rate. A loan with NHG gets the lower NHG rate but may
not exceed the NHG limit. The mortgage may not exceed the market value, so kosten koper and the
Direct nodig renovation come from equity and own funds.

Ages and the year's rules are taken at the expected levering, not today: that is the date the
startersvrijstelling and the lender's norms follow.
"""

from dataclasses import dataclass
from datetime import date

from app.buyer_profile import BuyerProfile, FinanceDraft, home_equity

# Below ten years fixed, the lender tests at the toetsrente.
LONG_FIXED_RATE_YEARS = 10


@dataclass(frozen=True)
class KostenKoper:
    transfer_tax: int
    fixed_costs: int
    nhg_fee: int
    total: int


@dataclass(frozen=True)
class Affordability:
    max_mortgage: int
    energy_label_bonus: int
    equity: int
    kosten_koper: KostenKoper | None
    mortgage_needed: int | None
    # What own funds lack for kosten koper and renovation, since the mortgage stops at the price.
    own_funds_shortfall: int | None
    # Gross monthly cost of the mortgage needed (annuity), and net of hypotheekrenteaftrek and
    # eigenwoningforfait in the first year.
    monthly_cost: int | None
    monthly_cost_net: int | None
    headroom: int | None
    # Highest purchase price the household can pay, kosten koper included (not the Walk-away
    # Maximum, which also weighs what the house is worth), after setting aside `renovation_direct`.
    affordable_maximum: int
    # The Renovation Estimate's Direct nodig midpoint, taken from the funds available for this house.
    renovation_direct: int = 0
    # Whether the mortgage needed at the asking price fits under the NHG limit, and the rate its
    # monthly cost is worked out at.
    nhg: bool | None = None
    mortgage_rate: float | None = None
    single_bonus: int = 0
    # What an NHG loan may include as standard for energy-saving measures on a label E, F or G
    # house. Named, never counted in the figures above: it is earmarked for the measures.
    nhg_energy_measures: int = 0


@dataclass(frozen=True)
class MarketRate:
    """Offered rates for ten years fixed, with and without NHG, as of one date."""

    as_of: date
    nhg: float
    no_nhg: float


@dataclass(frozen=True)
class Rules:
    version: int
    year: int
    toetsrente: float
    term_months: int
    max_ltv: float
    # Upper bounds of the toetsrente columns; a rate above the last falls in one more column.
    rate_bands: tuple[float, ...]
    # (lowest toetsinkomen, financieringslastpercentage per column), ascending.
    ratio_rows: tuple[tuple[int, tuple[float, ...]], ...]
    debt_gross_up: tuple[float, ...]
    single_bonus: int
    single_bonus_above_income: int
    energy_label_bonus: dict[str, int]
    nhg_limit: int
    nhg_fee_rate: float
    nhg_energy_measures_efg: int
    nhg_limit_with_measures: int
    transfer_tax_rate: float
    starter_min_age: int
    starter_max_age: int
    starter_price_limit: int
    interest_deduction_rate: float
    forfait_rate: float
    forfait_high_rate: float
    forfait_threshold: int
    fixed_costs: int
    market_rate: MarketRate

    @classmethod
    def from_table(cls, version: int, year: int, table: dict, market_rate: dict) -> "Rules":
        tax = table["transfer_tax"]
        ratio = table["financing_ratio"]
        income_tax = table["tax"]
        return cls(
            version=version,
            year=year,
            toetsrente=table["toetsrente"],
            term_months=table["term_months"],
            max_ltv=table["max_ltv"],
            rate_bands=tuple(ratio["rate_bands"]),
            ratio_rows=tuple((row["from"], tuple(p / 100 for p in row["percent"])) for row in ratio["rows"]),
            debt_gross_up=tuple(table["debt_gross_up"]["factors"]),
            single_bonus=table["single_bonus"]["amount"],
            single_bonus_above_income=table["single_bonus"]["above_income"],
            energy_label_bonus=table["energy_label_bonus"],
            nhg_limit=table["nhg"]["limit"],
            nhg_fee_rate=table["nhg"]["fee_rate"],
            nhg_energy_measures_efg=table["nhg"]["energy_measures_efg"],
            nhg_limit_with_measures=table["nhg"]["limit_with_measures"],
            transfer_tax_rate=tax["rate"],
            starter_min_age=tax["starter_min_age"],
            starter_max_age=tax["starter_max_age"],
            starter_price_limit=tax["starter_price_limit"],
            interest_deduction_rate=income_tax["interest_deduction_rate"],
            forfait_rate=income_tax["forfait_rate"],
            forfait_high_rate=income_tax["forfait_high_rate"],
            forfait_threshold=income_tax["forfait_threshold"],
            fixed_costs=sum(table["fixed_costs"].values()),
            market_rate=MarketRate(market_rate["as_of"], market_rate["nhg"], market_rate["no_nhg"]),
        )


def rules_summary(rules: Rules, levering: date) -> dict:
    """Which year's rules a figure rests on; `is_current_year` is false when no table exists yet
    for the year of the expected levering."""
    return {
        "version": rules.version,
        "year": rules.year,
        "is_current_year": rules.year == levering.year,
        "levering_on": levering.isoformat(),
        "market_rate_as_of": rules.market_rate.as_of.isoformat(),
    }


@dataclass(frozen=True)
class Consequences:
    """What a Buyer Profile can buy before any Listing is involved (the Gevolgen panel)."""

    max_mortgage: int
    equity: int
    budget: int  # highest purchase price payable, after kosten koper


Finances = BuyerProfile | FinanceDraft


def _annuity_factor(annual_rate: float, months: int) -> float:
    """Principal that one euro a month repays over the term."""
    monthly_rate = annual_rate / 12
    return (1 - (1 + monthly_rate) ** -months) / monthly_rate


def _age(born: date, on: date) -> int:
    return on.year - born.year - ((on.month, on.day) < (born.month, born.day))


def _adults(profile: Finances) -> list:
    return [m for m in profile.household if m.role == "adult"]


def _column(rules: Rules, rate: float) -> int:
    return next((i for i, bound in enumerate(rules.rate_bands) if rate <= bound + 1e-9), len(rules.rate_bands))


def _test_rate(profile: Finances, rules: Rules, offered: float) -> float:
    if profile.fixed_rate_years < LONG_FIXED_RATE_YEARS:
        return max(rules.toetsrente, offered)
    return offered


def _norm(profile: Finances, energy_label: str | None, rules: Rules, offered: float) -> tuple[int, int, int]:
    """Max mortgage by income at the offered rate, with its energy label bonus and single bonus."""
    rate = _test_rate(profile, rules, offered)
    column = _column(rules, rate)
    income = profile.gross_annual_income
    ratios = next(ratios for start, ratios in reversed(rules.ratio_rows) if income >= start)
    monthly = income * ratios[column] / 12 - profile.other_monthly_debt * rules.debt_gross_up[column]
    base = round(max(0.0, monthly) * _annuity_factor(rate, rules.term_months))
    label_bonus = rules.energy_label_bonus.get((energy_label or "").upper(), 0)
    single = rules.single_bonus if len(_adults(profile)) == 1 and income > rules.single_bonus_above_income else 0
    return base + label_bonus + single, label_bonus, single


@dataclass(frozen=True)
class _Capacity:
    with_nhg: int  # already capped at the NHG limit
    without_nhg: int
    label_bonus: int
    single_bonus: int

    @property
    def maximum(self) -> int:
        return max(self.with_nhg, self.without_nhg)


def _capacity(profile: Finances, energy_label: str | None, rules: Rules) -> _Capacity:
    nhg, label_bonus, single = _norm(profile, energy_label, rules, rules.market_rate.nhg)
    plain, _, _ = _norm(profile, energy_label, rules, rules.market_rate.no_nhg)
    return _Capacity(min(nhg, rules.nhg_limit), plain, label_bonus, single)


def _taxed_share(profile: Finances, price: int, rules: Rules, levering: date) -> float:
    """Share of the price transfer tax is due on: the startersvrijstelling is per buyer, for their
    own (equal) share, when the whole price is within the limit."""
    adults = _adults(profile)
    if not adults or price > rules.starter_price_limit:
        return 1.0
    exempt = sum(
        1
        for m in adults
        if not m.starter_exemption_used and rules.starter_min_age <= _age(m.birth_date, levering) <= rules.starter_max_age
    )
    return 1 - exempt / len(adults)


def _cash(profile: Finances) -> int:
    return home_equity(profile) + profile.assets.savings + profile.assets.investments


@dataclass(frozen=True)
class _Purchase:
    kosten_koper: KostenKoper
    # What the lender lends (at most `max_ltv` × the price), and what own funds must still cover
    # beyond that and do not have.
    mortgage: int
    shortfall: int
    nhg: bool


def _purchase(profile: Finances, price: int, rules: Rules, renovation: int, taxed_share: float, nhg: bool) -> _Purchase:
    """The loan a price needs once own funds have covered the renovation, then the rest. With NHG
    its fee counts with kosten koper. The lender lends at most the market value."""
    tax = round(price * rules.transfer_tax_rate * taxed_share)
    funds = max(0, _cash(profile) - renovation)
    before_fee = max(0, price + tax + rules.fixed_costs - funds)
    fee = round(before_fee * rules.nhg_fee_rate) if nhg and before_fee else 0
    wanted = before_fee + fee
    lent = min(wanted, int(rules.max_ltv * price))
    return _Purchase(
        KostenKoper(tax, rules.fixed_costs, fee, tax + rules.fixed_costs + fee), lent, wanted - lent, fee > 0
    )


def _routes(
    profile: Finances, price: int, rules: Rules, renovation: int, taxed_share: float, capacity: _Capacity
) -> list[tuple[_Purchase, int]]:
    """The loans a lender may offer for a price, cheapest first, each with what income allows: with
    NHG while the loan fits under the NHG limit, and always without."""
    plain = _purchase(profile, price, rules, renovation, taxed_share, nhg=False)
    routes = [(plain, capacity.without_nhg)]
    if 0 < plain.mortgage + plain.shortfall <= rules.nhg_limit:
        routes.insert(0, (_purchase(profile, price, rules, renovation, taxed_share, nhg=True), capacity.with_nhg))
    return routes


def _financed(
    profile: Finances, price: int, rules: Rules, renovation: int, taxed_share: float, capacity: _Capacity
) -> _Purchase | None:
    """The loan a lender would give: the renovation and kosten koper covered by own funds, and the
    loan within what income allows. None when no route works."""
    if renovation > _cash(profile):
        return None
    return next(
        (
            purchase
            for purchase, allowed in _routes(profile, price, rules, renovation, taxed_share, capacity)
            if purchase.shortfall == 0 and purchase.mortgage <= allowed
        ),
        None,
    )


def _highest_price(profile: Finances, rules: Rules, levering: date, renovation: int, capacity: _Capacity) -> int:
    """Highest financeable price. Within one transfer tax regime each loan route (with NHG, without)
    only gets harder as the price rises, so their union does too, and a binary search per regime
    finds it: the startersvrijstelling (up to its limit) and full tax (any price; harmlessly
    pessimistic below the limit)."""
    high = capacity.maximum + _cash(profile) + 1
    regimes = [(high, 1.0)]
    starter_share = _taxed_share(profile, min(rules.starter_price_limit, high), rules, levering)
    if starter_share < 1:
        regimes.append((min(rules.starter_price_limit, high), starter_share))
    best = 0
    for top, share in regimes:
        low, up = 0, top
        if _financed(profile, 1, rules, renovation, share, capacity) is None:
            continue
        while low < up:
            middle = (low + up + 1) // 2
            if _financed(profile, middle, rules, renovation, share, capacity) is not None:
                low = middle
            else:
                up = middle - 1
        best = max(best, low)
    return best


def _monthly_costs(loan: int, rate: float, price: int, rules: Rules) -> tuple[int, int]:
    """Gross annuity, and net of the first year's hypotheekrenteaftrek over interest less the
    eigenwoningforfait (the price standing in for the WOZ value)."""
    if loan == 0:
        return 0, 0
    gross = loan / _annuity_factor(rate, rules.term_months)
    forfait = min(price, rules.forfait_threshold) * rules.forfait_rate + max(0, price - rules.forfait_threshold) * rules.forfait_high_rate
    deductible = max(0.0, loan * rate - forfait) / 12
    return round(gross), round(gross - deductible * rules.interest_deduction_rate)


def consequences(draft: FinanceDraft, rules: Rules, levering: date) -> Consequences:
    capacity = _capacity(draft, None, rules)
    return Consequences(
        capacity.maximum, home_equity(draft), _highest_price(draft, rules, levering, 0, capacity)
    )


def compute(
    profile: BuyerProfile,
    asking_price: int | None,
    energy_label: str | None,
    rules: Rules,
    levering: date,
    renovation_direct: int = 0,
) -> Affordability:
    """`renovation_direct` (the Direct nodig midpoint of the house's Renovation Estimate) is set
    aside from the available funds before the affordable maximum is worked out."""
    capacity = _capacity(profile, energy_label, rules)
    equity = home_equity(profile)
    affordable_maximum = _highest_price(profile, rules, levering, renovation_direct, capacity)
    if asking_price is None:
        return Affordability(
            max_mortgage=capacity.maximum,
            energy_label_bonus=capacity.label_bonus,
            equity=equity,
            kosten_koper=None,
            mortgage_needed=None,
            own_funds_shortfall=None,
            monthly_cost=None,
            monthly_cost_net=None,
            headroom=None,
            affordable_maximum=affordable_maximum,
            renovation_direct=renovation_direct,
            single_bonus=capacity.single_bonus,
        )
    share = _taxed_share(profile, asking_price, rules, levering)
    # The route a lender would take; when none works, the cheapest one shows how far off it is.
    purchase = _financed(profile, asking_price, rules, renovation_direct, share, capacity) or _routes(
        profile, asking_price, rules, renovation_direct, share, capacity
    )[0][0]
    rate = rules.market_rate.nhg if purchase.nhg else rules.market_rate.no_nhg
    gross, net = _monthly_costs(purchase.mortgage, rate, asking_price, rules)
    return Affordability(
        max_mortgage=capacity.maximum,
        energy_label_bonus=capacity.label_bonus,
        equity=equity,
        kosten_koper=purchase.kosten_koper,
        mortgage_needed=purchase.mortgage,
        own_funds_shortfall=purchase.shortfall,
        monthly_cost=gross,
        monthly_cost_net=net,
        headroom=affordable_maximum - asking_price,
        affordable_maximum=affordable_maximum,
        renovation_direct=renovation_direct,
        nhg=purchase.nhg,
        mortgage_rate=rate,
        single_bonus=capacity.single_bonus,
        nhg_energy_measures=_nhg_energy_measures(energy_label, purchase, rules),
    )


def _nhg_energy_measures(energy_label: str | None, purchase: _Purchase, rules: Rules) -> int:
    """The standard NHG amount for energy measures, when this loan goes with NHG on a label E, F or
    G house and still fits under the NHG limit with the measures."""
    amount = rules.nhg_energy_measures_efg
    efg = (energy_label or "").strip().upper() in ("E", "F", "G")
    fits = purchase.nhg and purchase.mortgage + amount <= rules.nhg_limit_with_measures
    return amount if efg and amount and fits else 0
