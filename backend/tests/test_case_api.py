from tests.flag_rules import FLAG_RULES_VERSION
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
    assert affordability == {
        "max_mortgage": 496_660,
        "energy_label_bonus": 10_000,
        "kosten_koper": {"transfer_tax": 11_900, "fixed_costs": 5_050, "total": 16_950},
        "equity": 172_000,
        "mortgage_needed": 384_950,
        "monthly_cost": 1_838,
        "headroom": 109_519,
        "max_price": 704_519,
        "energy_label": "B",
    }
    assert case["rules"]["year"] == 2026


def test_low_income_starters_pay_no_transfer_tax_but_fall_far_short(client, listing_provider):
    capture(client, listing_provider, asking_price=300_000)
    client.put("/api/buyer-profile", json=low_income_profile())

    affordability = client.get("/api/listings/80907644/case").json()["affordability"]

    assert affordability["max_mortgage"] == 179_516
    assert affordability["kosten_koper"] == {"transfer_tax": 0, "fixed_costs": 5_050, "total": 5_050}
    assert affordability["equity"] == 0
    assert affordability["monthly_cost"] == 1_399
    assert affordability["headroom"] == -113_534


def test_starter_exemption_is_lost_above_the_price_limit(client, listing_provider):
    capture(client, listing_provider, asking_price=595_000)
    client.put("/api/buyer-profile", json=low_income_profile())

    affordability = client.get("/api/listings/80907644/case").json()["affordability"]

    assert affordability["kosten_koper"]["transfer_tax"] == 11_900
    assert affordability["monthly_cost"] == 2_864
    assert affordability["headroom"] == -408_534


def test_high_equity_household_has_large_headroom_and_no_mortgage_need(client, listing_provider):
    capture(client, listing_provider)
    client.put("/api/buyer-profile", json=high_equity_profile())

    affordability = client.get("/api/listings/80907644/case").json()["affordability"]

    assert affordability["equity"] == 780_000
    assert affordability["monthly_cost"] == 0
    assert affordability["headroom"] == 595_560


def test_energielabel_raises_borrowing_capacity(client, listing_provider):
    client.put("/api/buyer-profile", json=high_equity_profile())
    capture(client, listing_provider, energy_label="A+++")

    affordability = client.get("/api/listings/80907644/case").json()["affordability"]

    assert affordability["energy_label_bonus"] == 25_000
    assert affordability["max_mortgage"] == 304_422
    assert affordability["headroom"] == 610_266


def test_energielabel_without_bonus_leaves_capacity_unchanged(client, listing_provider):
    client.put("/api/buyer-profile", json=high_equity_profile())
    capture(client, listing_provider, energy_label="E")

    affordability = client.get("/api/listings/80907644/case").json()["affordability"]

    assert affordability["energy_label_bonus"] == 0
    assert affordability["max_mortgage"] == 279_422


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

    assert affordability["max_mortgage"] == 496_660
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
    assert case["affordability"]["max_mortgage"] == 624_729


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
        .replace("test_rate = 0.05", "test_rate = 0.04")
    )
    settings.affordability_rules_path = table
    capture(client, listing_provider)
    client.put("/api/buyer-profile", json=typical_profile())

    case = client.get("/api/listings/80907644/case").json()

    assert case["rules"] == {"year": 2001, "is_current_year": False}
    assert case["affordability"]["max_mortgage"] == 557_217

