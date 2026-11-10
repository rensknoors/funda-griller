from app import store
from tests.flag_rules import COST_TABLE_VERSION, FLAG_RULES_VERSION
from tests.listing_fixtures import LIVE_URL, live_listing
from tests.profile_fixtures import high_equity_profile, low_income_profile, typical_profile


def capture(client, listing_provider, **overrides):
    listing_provider.listings[LIVE_URL] = live_listing(**overrides)
    return client.post("/api/listings", json={"url": LIVE_URL}).json()


def test_case_shows_listing_facts_each_labelled_with_provenance(client, listing_provider):
    snapshot = capture(client, listing_provider)["snapshots"][0]

    response = client.get("/api/listings/80907644/case")

    assert response.status_code == 200
    facts = {fact["key"]: fact for fact in response.json()["facts"]}
    assert facts["asking_price"]["value"] == 595000
    assert facts["living_area"]["value"] == 152
    assert facts["energy_label"]["value"] == "B"
    assert facts["construction_year"]["value"] == 1931
    for fact in facts.values():
        assert fact["provenance"] == "listing"
        assert fact["fetched_at"] == snapshot["fetched_at"]


def test_case_for_unknown_listing_is_not_found(client):
    assert client.get("/api/listings/1/case").status_code == 404


def test_case_records_the_snapshot_and_profile_version_that_produced_it(client, listing_provider):
    snapshot = capture(client, listing_provider)["snapshots"][0]
    client.put("/api/buyer-profile", json=typical_profile())

    built_from = client.get("/api/listings/80907644/case").json()["built_from"]

    assert built_from | {"documents": None} == {
        "snapshot_id": snapshot["id"],
        "profile_version": 1,
        "flag_rules_version": FLAG_RULES_VERSION,
        "cost_table_version": COST_TABLE_VERSION,
        "price_index_version": 1,
        "bid_margins_version": 1,
        "observation_run": 1,
        "documents": None,
    }


def test_typical_household_affordability(client, listing_provider):
    capture(client, listing_provider)
    client.put("/api/buyer-profile", json=typical_profile())

    case = client.get("/api/listings/80907644/case").json()

    affordability = case["affordability"]
    assert affordability.pop("provenance") == "computed"
    assert affordability.pop("computed_on")
    assert affordability.pop("computed_at") == "2026-10-24T12:00:00+00:00"
    # 2027 rules, ten years fixed with NHG at 4,40%: 27,4% of €95.000 plus €10.000 for label B.
    # €384.950 to borrow fits under the NHG limit, so the 0,4% fee (€1.540) is added.
    assert affordability == {
        "max_mortgage": 443_174,
        "energy_label_bonus": 10_000,
        "single_bonus": 0,
        "nhg_energy_measures": 0,
        "kosten_koper": {"transfer_tax": 11_900, "fixed_costs": 5_050, "nhg_fee": 1_540, "total": 18_490},
        "equity": 172_000,
        "mortgage_needed": 386_490,
        "own_funds_shortfall": 0,
        "nhg": True,
        "mortgage_rate": 0.044,
        "monthly_cost": 1_935,
        "monthly_cost_net": 1_461,
        "headroom": 55_351,
        "affordable_maximum": 650_351,
        "renovation_direct": 0,
        "energy_label": "B",
        "rates": {
            "nhg": {"rate": 0.044, "source": "market", "as_of": "2026-11-02"},
            "no_nhg": {"rate": 0.0478, "source": "market", "as_of": "2026-11-02"},
        },
    }
    assert case["rules"]["year"] == 2027


def test_low_income_starters_pay_no_transfer_tax_but_fall_far_short(client, listing_provider):
    capture(client, listing_provider, asking_price=300_000)
    client.put("/api/buyer-profile", json=low_income_profile())

    affordability = client.get("/api/listings/80907644/case").json()["affordability"]

    assert affordability["max_mortgage"] == 178_444
    assert affordability["kosten_koper"]["transfer_tax"] == 0
    assert affordability["equity"] == 0
    assert affordability["monthly_cost"] == 1_473
    assert affordability["headroom"] == -115_317


def test_starter_exemption_is_lost_above_the_price_limit(client, listing_provider):
    capture(client, listing_provider, asking_price=620_000)
    client.put("/api/buyer-profile", json=low_income_profile())

    affordability = client.get("/api/listings/80907644/case").json()["affordability"]

    # Above the 2027 limit of €615.000; €625.450 to borrow is over the NHG limit, so 4,78%. The
    # lender stops at the price: €5.450 of kosten koper has no own funds behind it.
    assert affordability["kosten_koper"]["transfer_tax"] == 12_400
    assert affordability["nhg"] is False
    assert affordability["mortgage_needed"] == 620_000
    assert affordability["own_funds_shortfall"] == 5_450
    assert affordability["monthly_cost"] == 3_245
    assert affordability["headroom"] == -435_317


def test_high_equity_household_has_large_headroom_and_no_mortgage_need(client, listing_provider):
    capture(client, listing_provider)
    client.put("/api/buyer-profile", json=high_equity_profile())

    affordability = client.get("/api/listings/80907644/case").json()["affordability"]

    assert affordability["equity"] == 780_000
    assert affordability["monthly_cost"] == 0
    assert affordability["monthly_cost_net"] == 0
    assert affordability["headroom"] == 556_554


def test_energielabel_raises_borrowing_capacity(client, listing_provider):
    client.put("/api/buyer-profile", json=high_equity_profile())
    capture(client, listing_provider, energy_label="A+++")

    affordability = client.get("/api/listings/80907644/case").json()["affordability"]

    assert affordability["energy_label_bonus"] == 25_000
    assert affordability["max_mortgage"] == 265_634
    assert affordability["headroom"] == 571_202  # €1.166.202: tax and NHG fee rounded to the euro


def test_energielabel_without_bonus_leaves_capacity_unchanged(client, listing_provider):
    client.put("/api/buyer-profile", json=high_equity_profile())
    capture(client, listing_provider, energy_label="E")

    affordability = client.get("/api/listings/80907644/case").json()["affordability"]

    assert affordability["energy_label_bonus"] == 0
    assert affordability["max_mortgage"] == 240_634


def test_case_without_a_profile_has_facts_but_no_affordability(client, listing_provider):
    capture(client, listing_provider)

    case = client.get("/api/listings/80907644/case").json()

    assert case["affordability"] is None
    assert case["built_from"]["profile_version"] is None
    assert case["facts"]


def test_listing_without_asking_price_still_gets_maximum_mortgage(client, listing_provider):
    capture(client, listing_provider, asking_price=None)
    client.put("/api/buyer-profile", json=typical_profile())

    affordability = client.get("/api/listings/80907644/case").json()["affordability"]

    assert affordability["max_mortgage"] == 443_174
    assert affordability["kosten_koper"] is None
    assert affordability["monthly_cost"] is None
    assert affordability["headroom"] is None


def test_case_is_rebuilt_when_the_profile_changes(client, listing_provider):
    capture(client, listing_provider)
    client.put("/api/buyer-profile", json=typical_profile())
    richer = typical_profile() | {"gross_annual_income": 120_000}
    client.put("/api/buyer-profile", json=richer)

    case = client.get("/api/listings/80907644/case").json()

    assert case["built_from"]["profile_version"] == 2
    # 29,4% of €120.000 at 4,78% without NHG plus label B; with NHG it would be capped at €500.000.
    assert case["affordability"]["max_mortgage"] == 571_651


def test_case_is_rebuilt_when_the_snapshot_changes(client, listing_provider):
    capture(client, listing_provider)
    client.put("/api/buyer-profile", json=typical_profile())
    listing_provider.listings[LIVE_URL] = live_listing(asking_price=550_000)
    refetched = client.post("/api/listings/80907644/refetch").json()

    case = client.get("/api/listings/80907644/case").json()

    assert case["built_from"]["snapshot_id"] == refetched["snapshots"][0]["id"]
    assert {f["key"]: f for f in case["facts"]}["asking_price"]["value"] == 550_000
    assert case["affordability"]["kosten_koper"]["transfer_tax"] == 11_000


def test_case_carries_no_raw_income_or_balances(client, listing_provider):
    capture(client, listing_provider)
    profile = typical_profile() | {
        "gross_annual_income": 87_654,
        "assets": {"savings": 43_210, "investments": 9_876},
    }
    client.put("/api/buyer-profile", json=profile)

    body = client.get("/api/listings/80907644/case").text

    for raw in ("income", "savings", "investments", "87654", "43210", "9876"):
        assert raw not in body


def test_rules_come_from_the_table_for_the_year_and_the_year_is_shown(
    client, listing_provider, settings, tmp_path
):
    table = tmp_path / "rules.toml"
    table.write_text(
        (settings.affordability_rules_path.read_text())
        .replace("[years.2026", "[years.2001")
        .replace("[years.2027", "[years.2002")
        .replace("limit = 500000", "limit = 400000")
    )
    settings.affordability_rules_path = table
    capture(client, listing_provider)
    client.put("/api/buyer-profile", json=typical_profile())

    case = client.get("/api/listings/80907644/case").json()

    assert case["rules"]["year"] == 2002
    assert case["rules"]["is_current_year"] is False
    # The 2002 NHG limit caps the NHG route, so the loan without NHG (28,4% at 4,78%, label B) wins.
    assert case["affordability"]["max_mortgage"] == 439_516



def starters(*birth_dates: str, used: tuple[bool, ...] = ()) -> dict:
    """The low-income profile with these adults; `used` marks who used the startersvrijstelling."""
    used = used or (False,) * len(birth_dates)
    return {
        **low_income_profile(),
        "household": [
            {"role": "adult", "birth_date": born, "starter_exemption_used": was_used}
            for born, was_used in zip(birth_dates, used, strict=True)
        ],
    }


def transfer_tax(client, listing_provider, profile: dict, asking_price: int = 595_000) -> int:
    capture(client, listing_provider, asking_price=asking_price)
    client.put("/api/buyer-profile", json=profile)
    return client.get("/api/listings/80907644/case").json()["affordability"]["kosten_koper"]["transfer_tax"]


def test_startersvrijstelling_covers_only_the_young_buyers_share(client, listing_provider):
    """Levering 2027-01-24: one buyer is 30, the other 36, so 2% on half of €595.000."""
    assert transfer_tax(client, listing_provider, starters("1996-06-01", "1990-06-01")) == 5_950


def test_a_buyer_who_used_the_startersvrijstelling_pays_on_their_share(client, listing_provider):
    profile = starters("1996-06-01", "1997-06-01", used=(True, False))

    assert transfer_tax(client, listing_provider, profile) == 5_950


def test_a_buyer_turning_35_before_levering_is_no_starter(client, listing_provider):
    """34 today (2026-10-24), 35 at the expected levering (2027-01-24)."""
    assert transfer_tax(client, listing_provider, starters("1992-01-01", "1997-06-01")) == 5_950


def test_startersvrijstelling_holds_up_to_the_2027_limit(client, listing_provider):
    assert transfer_tax(client, listing_provider, starters("1996-06-01", "1997-06-01"), asking_price=615_000) == 0


def test_startersvrijstelling_is_lost_one_euro_above_the_2027_limit(client, listing_provider):
    profile = starters("1996-06-01", "1997-06-01")

    assert transfer_tax(client, listing_provider, profile, asking_price=615_001) == 12_300


def test_a_mortgage_under_the_nhg_limit_carries_the_fee_and_the_nhg_rate(client, listing_provider):
    """Starters, €300.000, €12.000 saved: €293.050 to borrow, 0,4% fee (€1.172), at 4,40% with NHG.
    Net: less 38,16% of (interest − 0,35% eigenwoningforfait) / 12."""
    capture(client, listing_provider, asking_price=300_000)
    client.put("/api/buyer-profile", json=low_income_profile())

    affordability = client.get("/api/listings/80907644/case").json()["affordability"]

    assert affordability["kosten_koper"] == {"transfer_tax": 0, "fixed_costs": 5_050, "nhg_fee": 1_172, "total": 6_222}
    assert affordability["mortgage_needed"] == 294_222
    assert affordability["nhg"] is True
    assert affordability["mortgage_rate"] == 0.044
    assert affordability["monthly_cost"] == 1_473
    assert affordability["monthly_cost_net"] == 1_095


def test_monthly_cost_is_at_the_own_rate_of_the_route_taken(client, listing_provider):
    """The same €294.222 with NHG at an own 4%: €294.222 / 209,46 annuity factor is €1.405 gross;
    net less 38,16% of (4% interest − €1.050 eigenwoningforfait) / 12 is €1.064."""
    capture(client, listing_provider, asking_price=300_000)
    client.put("/api/buyer-profile", json={**low_income_profile(), "offered_rate_nhg": 0.04})

    case = client.get("/api/listings/80907644/case").json()

    affordability = case["affordability"]
    assert affordability["nhg"] is True
    assert affordability["mortgage_rate"] == 0.04
    assert (affordability["monthly_cost"], affordability["monthly_cost_net"]) == (1_405, 1_064)
    assert affordability["rates"]["nhg"] == {"rate": 0.04, "source": "own", "as_of": None}
    assert case["rules"]["rates"]["nhg"]["source"] == "own"


def test_a_profile_saved_before_own_rates_rests_on_the_market_rates(client, listing_provider, settings):
    capture(client, listing_provider)
    store.save_buyer_profile(settings.database_path, typical_profile())

    case = client.get("/api/listings/80907644/case").json()

    assert case["affordability"]["max_mortgage"] == 443_174
    assert {route["source"] for route in case["affordability"]["rates"].values()} == {"market"}


def test_an_own_rate_without_nhg_leaves_the_cost_of_an_nhg_loan_alone(client, listing_provider):
    capture(client, listing_provider, asking_price=300_000)
    client.put("/api/buyer-profile", json={**low_income_profile(), "offered_rate_no_nhg": 0.04})

    affordability = client.get("/api/listings/80907644/case").json()["affordability"]

    assert affordability["mortgage_rate"] == 0.044
    assert affordability["monthly_cost"] == 1_473
    assert affordability["rates"]["nhg"]["source"] == "market"


def test_the_mortgage_needed_stops_at_the_price_and_the_rest_is_a_shortfall(client, listing_provider):
    """Starters without savings at €300.000: €305.050 with fixed costs, €306.270 with the NHG fee.
    A lender lends at most the price, so €6.270 must come from own funds that are not there."""
    capture(client, listing_provider, asking_price=300_000)
    client.put("/api/buyer-profile", json={**low_income_profile(), "assets": {"savings": 0, "investments": 0}})

    affordability = client.get("/api/listings/80907644/case").json()["affordability"]

    assert affordability["mortgage_needed"] == 300_000
    assert affordability["own_funds_shortfall"] == 6_270


def test_an_e_f_or_g_label_names_the_nhg_room_for_energy_measures_without_counting_it(client, listing_provider):
    """NHG 2027: on a label E, F or G house a loan with NHG includes €20.000 for energy-saving
    measures as standard. It is earmarked for the measures, so the figures leave it out."""
    capture(client, listing_provider, energy_label="E")
    client.put("/api/buyer-profile", json=typical_profile())

    affordability = client.get("/api/listings/80907644/case").json()["affordability"]

    assert affordability["nhg_energy_measures"] == 20_000
    assert affordability["max_mortgage"] == 433_174


def test_no_nhg_energy_room_for_a_better_label(client, listing_provider):
    capture(client, listing_provider, energy_label="B")
    client.put("/api/buyer-profile", json=typical_profile())

    assert client.get("/api/listings/80907644/case").json()["affordability"]["nhg_energy_measures"] == 0


def test_no_nhg_energy_room_before_2027(client, listing_provider, settings):
    settings.expected_levering_months = 0
    capture(client, listing_provider, energy_label="E")
    client.put("/api/buyer-profile", json=typical_profile())

    assert client.get("/api/listings/80907644/case").json()["affordability"]["nhg_energy_measures"] == 0


def test_no_nhg_energy_room_named_when_the_loan_goes_without_nhg(client, listing_provider):
    """€505.000 to borrow is over the €500.000 NHG limit, so no NHG and no standard energy amount,
    although €525.000 with it would fit under €530.000."""
    capture(client, listing_provider, energy_label="E")
    profile = {**typical_profile(), "gross_annual_income": 150_000, "current_home": None}
    client.put("/api/buyer-profile", json={**profile, "assets": {"savings": 106_950, "investments": 0}})

    affordability = client.get("/api/listings/80907644/case").json()["affordability"]

    assert (affordability["mortgage_needed"], affordability["nhg"]) == (505_000, False)
    assert affordability["nhg_energy_measures"] == 0


def test_the_asking_price_margin_is_a_rule_value_with_its_time(client, listing_provider):
    capture(client, listing_provider)

    margin = client.get("/api/listings/80907644/case").json()["asking_price_margin"]

    assert margin["provenance"] == "rule"
    assert margin["computed_at"] == "2026-10-24T12:00:00+00:00"
