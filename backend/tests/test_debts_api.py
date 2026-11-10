"""Debts by kind: each debt in the Buyer Profile weighs on the maximum mortgage the way the norms say.

Hand-computed examples on a couple with €70.000 in 2027 (Nibud, Advies hypotheeknormen 2027): at
4,25% (ten years fixed) 24,8% of the income is €1.446,67 a month, at 5% (five years fixed) 25,7% is
€1.499,17. The debt's monthly toetslast times the Trhk art. 3a gross-up (1,25 at 4,25%, 1,30 at 5%)
comes off that before the 30-year annuity at the test rate turns it into a mortgage (€203,27 of
mortgage per euro a month at 4,25%, €186,28 at 5%).
"""

import pytest

from app import store
from tests.profile_fixtures import typical_profile
from tests.test_profile_consequences import couple, offered_rate

CONSEQUENCES = "/api/buyer-profile/consequences"

STUDY_LOAN_SF35 = {"kind": "study_loan", "debt": 30_000, "interest_rate": 0.025, "stelsel": "SF35"}
STUDY_LOAN_SF15 = {**STUDY_LOAN_SF35, "stelsel": "SF15"}


def max_mortgage(client, fixed_rate_years: int, *debts: dict) -> int:
    response = client.post(CONSEQUENCES, json=couple(70_000, fixed_rate_years=fixed_rate_years, debts=list(debts)))
    assert response.status_code == 200, response.json()
    return response.json()["max_mortgage"]


@pytest.fixture
def at_425(settings, tmp_path):
    offered_rate(settings, tmp_path, "0.0425")


def test_without_debts_the_norm_is_unchanged(client, at_425):
    assert max_mortgage(client, 10) == 294_074


@pytest.mark.parametrize(
    ("loan", "ten_years", "five_years"),
    [
        # €30.000 at 2,5% over 420 months: €107,25 a month (DUO wettelijk maandbedrag).
        # (1.446,67 − 107,25 × 1,25) × 203,27 and (1.499,17 − 107,25 × 1,30) × 186,28.
        (STUDY_LOAN_SF35, 266_822, 253_295),
        # The same over 180 months: €200,04 a month.
        (STUDY_LOAN_SF15, 243_244, 230_824),
    ],
)
def test_a_study_loan_weighs_by_its_wettelijk_maandbedrag(client, at_425, loan, ten_years, five_years):
    assert max_mortgage(client, 10, loan) == ten_years
    # Under ten years fixed the test rate is the 5% toetsrente, whatever the offered rate.
    assert max_mortgage(client, 5, loan) == five_years


def test_a_mijn_duo_amount_overrides_the_derived_wettelijk_maandbedrag(client, at_425):
    # €200 a month instead of the derived €107,25: (1.446,67 − 200 × 1,25) × 203,27.
    assert max_mortgage(client, 10, {**STUDY_LOAN_SF35, "monthly_override": 200}) == 243_255


def test_a_revolving_credit_limit_lowers_the_maximum_even_when_nothing_is_drawn(client, at_425):
    # Gedragscode Hypothecaire Financieringen §4 lid 5: 2% of the €5.000 limit is €100 a month.
    assert max_mortgage(client, 10, {"kind": "revolving_credit", "limit": 5_000}) == 268_664


def test_a_private_lease_weighs_by_its_monthly_lease_term(client, at_425):
    # €300 a month in full (UNVERIFIED share, see config): (1.446,67 − 300 × 1,25) × 203,27.
    assert max_mortgage(client, 10, {"kind": "private_lease", "monthly_term": 300}) == 217_845


def test_an_instalment_loan_weighs_by_its_contractual_monthly_term(client, at_425):
    # Gedragscode §4 lid 5: at least the contractual interest and repayment, €150 a month.
    assert max_mortgage(client, 10, {"kind": "instalment_loan", "monthly_term": 150}) == 255_959


def test_several_debts_together_cost_the_sum_of_their_separate_effects(client, at_425):
    debts = (
        STUDY_LOAN_SF35,
        {"kind": "revolving_credit", "limit": 5_000},
        {"kind": "private_lease", "monthly_term": 300},
        {"kind": "instalment_loan", "monthly_term": 150},
    )
    without = max_mortgage(client, 10)
    separate = sum(without - max_mortgage(client, 10, debt) for debt in debts)

    together = without - max_mortgage(client, 10, *debts)

    # Each figure is rounded to the euro on its own.
    assert abs(together - separate) <= len(debts)
    assert together == 294_074 - 127_069


def test_gevolgen_show_per_debt_its_toetslast_and_the_leenruimte_it_costs(client, at_425):
    debts = [STUDY_LOAN_SF35, {"kind": "revolving_credit", "limit": 5_000}]

    consequences = client.post(CONSEQUENCES, json=couple(70_000, fixed_rate_years=10, debts=debts)).json()

    # What each debt costs: the maximum without it, less the maximum with every debt. Both debts:
    # (1.446,67 − 207,25 × 1,25) × 203,27 = €241.412; without the study loan €268.664 (above),
    # without the credit €266.822.
    assert consequences["max_mortgage"] == 241_412
    assert consequences["debts"] == [
        {"kind": "study_loan", "toetslast": 107.25, "costs": 268_664 - 241_412},
        {"kind": "revolving_credit", "toetslast": 100.0, "costs": 266_822 - 241_412},
    ]


def test_a_profile_stored_with_one_monthly_debt_reads_back_as_one_other_debt(client, settings, at_425):
    legacy = {**typical_profile(), "other_monthly_debt": 70}
    del legacy["debts"]
    store.save_buyer_profile(settings.database_path, legacy)

    profile = client.get("/api/buyer-profile").json()["profile"]

    assert "other_monthly_debt" not in profile
    assert profile["debts"] == [{"kind": "other", "monthly": 70}]


def test_a_draft_with_one_monthly_debt_keeps_its_figures(client, at_425):
    """Nibud advies 2027 §5.1: at 4,25% €70 a month costs ≈ €17.787 of mortgage (gross-up 1,25)."""
    consequences = client.post(CONSEQUENCES, json=couple(70_000, fixed_rate_years=10, other_monthly_debt=70)).json()

    assert consequences["max_mortgage"] == 294_074 - 17_787
    assert consequences["debts"] == [{"kind": "other", "toetslast": 70.0, "costs": 17_787}]


@pytest.mark.parametrize(
    ("debt", "field", "message"),
    [
        ({"kind": "lening"}, "debts.0.kind", "Kies een soort schuld"),
        ({"kind": "study_loan", "debt": 30_000, "interest_rate": 0.025}, "debts.0.stelsel", "Verplicht veld"),
        ({**STUDY_LOAN_SF35, "interest_rate": 0.25}, "debts.0.interest_rate", "Kies een rente van 0 tot 15%"),
        ({**STUDY_LOAN_SF35, "stelsel": "SF20"}, "debts.0.stelsel", "Kies SF35 of SF15"),
        ({"kind": "revolving_credit", "limit": -1}, "debts.0.limit", "Bedrag buiten bereik"),
        ({"kind": "revolving_credit"}, "debts.0.limit", "Verplicht veld"),
        ({"kind": "instalment_loan"}, "debts.0.monthly_term", "Verplicht veld"),
        ({"kind": "private_lease", "monthly_term": 100_001}, "debts.0.monthly_term", "Bedrag buiten bereik"),
        ({"kind": "other", "monthly": -5}, "debts.0.monthly", "Bedrag buiten bereik"),
    ],
)
def test_the_buyer_profile_checks_each_kind_of_debts_fields(client, debt, field, message):
    response = client.post("/api/buyer-profile/validation", json={**typical_profile(), "debts": [debt]})

    assert response.json()["errors"] == [{"field": field, "message": message}]


def test_each_kind_of_debt_is_saved_and_read_back(client):
    debts = [
        {**STUDY_LOAN_SF35, "monthly_override": 120},
        {"kind": "revolving_credit", "limit": 2_500},
        {"kind": "instalment_loan", "monthly_term": 150},
        {"kind": "private_lease", "monthly_term": 300},
        {"kind": "other", "monthly": 40},
    ]

    assert client.put("/api/buyer-profile", json={**typical_profile(), "debts": debts}).status_code == 200

    stored = client.get("/api/buyer-profile").json()["profile"]["debts"]
    assert stored == [{**STUDY_LOAN_SF35, "monthly_override": 120}, *debts[1:]]
