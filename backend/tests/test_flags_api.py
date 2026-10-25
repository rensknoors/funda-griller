import tomllib

import pytest

from app.ports import SourceFact
from tests.listing_fixtures import LIVE_URL, live_listing
from tests.profile_fixtures import low_income_profile, typical_profile


def case_for(client, listing_provider, profile=None, **listing_overrides):
    listing_provider.listings[LIVE_URL] = live_listing(**listing_overrides)
    client.post("/api/listings", json={"url": LIVE_URL})
    if profile is not None:
        client.put("/api/buyer-profile", json=profile)
    return client.get("/api/listings/80907644/case").json()


def flags_by_rule(case):
    return {flag["rule_id"]: flag for flag in case["flags"]}


def evidence(flag):
    return {item["key"]: item["value"] for item in flag["evidence"]}


def test_energielabel_worse_than_the_renovation_tolerance_allows_is_a_con(client, listing_provider):
    move_in_ready = typical_profile() | {"renovation_tolerance": 1}

    case = case_for(client, listing_provider, move_in_ready, energy_label="E")

    flag = flags_by_rule(case)["energy_label_below_tolerance"]
    assert flag["class"] == "con"
    assert flag["rule_version"] == 2
    assert evidence(flag)["energy_label"] == "E"
    assert evidence(flag)["worst_acceptable_energy_label"] == "C"


def test_an_energy_efficient_label_is_a_pro(client, listing_provider):
    case = case_for(client, listing_provider, typical_profile(), energy_label="A++")

    flag = flags_by_rule(case)["energy_label_efficient"]
    assert flag["class"] == "pro"
    assert evidence(flag) == {"energy_label": "A++", "threshold": "A"}


def test_the_same_energielabel_passes_for_a_household_ready_to_renovate(client, listing_provider):
    case = case_for(client, listing_provider, typical_profile(), energy_label="E")

    assert "energy_label_below_tolerance" not in flags_by_rule(case)


def test_editing_the_rules_produces_a_new_case_version(client, listing_provider, settings, tmp_path):
    first = case_for(client, listing_provider, typical_profile(), energy_label="E")
    version = tomllib.loads(settings.flag_rules_path.read_text())["version"]
    stricter = tmp_path / "flag_rules.toml"
    stricter.write_text(
        settings.flag_rules_path.read_text()
        .replace(f"version = {version}\n", f"version = {version + 1}\n", 1)
        .replace("3 = \"E\"", "3 = \"D\"")
    )
    settings.flag_rules_path = stricter

    second = client.get("/api/listings/80907644/case").json()

    assert first["built_from"]["flag_rules_version"] == version
    assert second["built_from"]["flag_rules_version"] == version + 1
    assert "energy_label_below_tolerance" in flags_by_rule(second)


def test_asking_price_beyond_affordability_headroom_is_a_con(client, listing_provider):
    case = case_for(client, listing_provider, low_income_profile(), asking_price=300_000)

    flag = flags_by_rule(case)["ask_beyond_headroom"]
    assert flag["class"] == "con"
    assert evidence(flag) == {"headroom": -113_534, "asking_price": 300_000, "threshold": 0}


def test_without_a_woz_value_the_overpricing_rule_raises_nothing(client, listing_provider):
    case = case_for(client, listing_provider, typical_profile(), asking_price=2_000_000)

    assert "ask_far_above_woz" not in flags_by_rule(case)


def test_a_must_have_the_listing_does_not_mention_is_a_con(client, listing_provider):
    profile = typical_profile() | {"must_haves": ["Een garage", "Grote tuin"]}

    case = case_for(client, listing_provider, profile, description="Vrijstaande woning met garage.")

    missing = [flag for flag in case["flags"] if flag["rule_id"] == "must_have_missing"]
    assert len(missing) == 1
    assert missing[0]["class"] == "con"
    assert evidence(missing[0]) == {"must_have": "Grote tuin", "tuin_mentioned": False}


def test_a_deal_breaker_the_listing_mentions_forces_hard_no(client, listing_provider):
    profile = typical_profile() | {"deal_breakers": ["Geen erfpacht"]}

    case = case_for(
        client, listing_provider, profile, description="Appartement op erfpacht, canon afgekocht."
    )

    assert case["hard_no"] == {
        "tier": "hard_no",
        "deal_breaker": "Geen erfpacht",
        "flag_id": "deal_breaker_mentioned:Geen erfpacht",
    }
    flag = {f["id"]: f for f in case["flags"]}["deal_breaker_mentioned:Geen erfpacht"]
    assert flag["class"] == "con"
    assert evidence(flag) == {"deal_breaker": "Geen erfpacht", "erfpacht_mentioned": True}


def test_a_deal_breaker_naming_a_raised_flag_forces_hard_no(client, listing_provider):
    profile = low_income_profile() | {"deal_breakers": ["Alles boven budget"]}

    case = case_for(client, listing_provider, profile, asking_price=300_000)

    assert case["hard_no"] == {
        "tier": "hard_no",
        "deal_breaker": "Alles boven budget",
        "flag_id": "ask_beyond_headroom",
    }


def test_deal_breakers_the_case_does_not_hit_leave_no_hard_no(client, listing_provider):
    profile = typical_profile() | {"deal_breakers": ["Geen erfpacht", "Alles boven budget"]}

    case = case_for(client, listing_provider, profile, description="Vrijstaande woning met garage.")

    assert case["hard_no"] is None
    assert case["flags"] == []


def test_the_register_energielabel_outranks_the_listing_claim_in_flags(
    client, listing_provider, source_clients
):
    source_clients["energielabel"].facts = [SourceFact(name="energy_label", value="A")]

    case = case_for(client, listing_provider, typical_profile(), energy_label="E")

    flag = flags_by_rule(case)["energy_label_efficient"]
    [label] = [item for item in flag["evidence"] if item["key"] == "energy_label"]
    assert (label["value"], label["provenance"], label["source"]) == ("A", "source", "energielabel")


def test_asking_price_far_above_woz_is_a_con(client, listing_provider, source_clients):
    source_clients["woz"].facts = [
        SourceFact(name="woz_value", value=450_000, as_of="2024-01-01"),
        SourceFact(name="woz_value", value=500_000, as_of="2025-01-01"),
    ]

    case = case_for(client, listing_provider, typical_profile(), asking_price=595_000)

    flag = flags_by_rule(case)["ask_far_above_woz"]
    assert flag["class"] == "con"
    assert evidence(flag) == {
        "asking_price": 595_000,
        "woz_value": 500_000,
        "asking_vs_woz": 1.19,
        "threshold": 1.15,
    }


def test_a_listing_that_says_it_has_no_garage_does_not_hit_a_geen_garage_deal_breaker(
    client, listing_provider
):
    profile = typical_profile() | {"deal_breakers": ["Geen garage"]}

    case = case_for(client, listing_provider, profile, description="Tussenwoning, geen garage.")

    assert case["hard_no"] is None


def test_a_negated_deal_breaker_is_hit_when_the_listing_has_the_feature(client, listing_provider):
    profile = typical_profile() | {"deal_breakers": ["Niet op erfpacht"]}

    case = case_for(
        client, listing_provider, profile, description="Geen garage. Gelegen op eeuwigdurende erfpacht."
    )

    assert case["hard_no"]["deal_breaker"] == "Niet op erfpacht"


def test_a_must_have_the_listing_says_it_lacks_is_missing(client, listing_provider):
    profile = typical_profile() | {"must_haves": ["Garage"]}

    case = case_for(client, listing_provider, profile, description="Woning zonder garage, wel een tuin.")

    missing = [flag for flag in case["flags"] if flag["rule_id"] == "must_have_missing"]
    assert [evidence(flag) for flag in missing] == [{"must_have": "Garage", "garage_mentioned": False}]


def test_a_compound_in_the_description_counts_as_its_feature(client, listing_provider):
    profile = typical_profile() | {"must_haves": ["Tuin"]}

    case = case_for(client, listing_provider, profile, description="Diepe achtertuin op het zuiden.")

    assert "must_have_missing" not in flags_by_rule(case)


def test_a_deal_breaker_only_containing_a_rule_alias_inside_a_word_is_not_hit(
    client, listing_provider, llm_client
):
    llm_client.observations = [{"key": "roof_condition", "value": "poor", "photos": [1]}]
    profile = typical_profile() | {"deal_breakers": ["Geen dakterras"]}

    case = case_for(client, listing_provider, profile, description="Ruime woning.")

    assert "roof_poor" in flags_by_rule(case)
    assert case["hard_no"] is None


@pytest.mark.parametrize(("label", "hit"), [("E", False), ("F", True), ("G", True)])
def test_an_energielabel_deal_breaker_is_hit_only_by_the_labels_it_names(
    client, listing_provider, label, hit
):
    profile = typical_profile() | {"renovation_tolerance": 1, "deal_breakers": ["Energielabel F of G"]}

    case = case_for(client, listing_provider, profile, energy_label=label)

    assert "energy_label_below_tolerance" in flags_by_rule(case)
    assert (case["hard_no"] is not None) == hit
    if hit:
        flag = {f["id"]: f for f in case["flags"]}[case["hard_no"]["flag_id"]]
        assert evidence(flag)["energy_label"] == label
        assert evidence(flag)["named_energy_labels"] == ["F", "G"]


def test_an_energielabel_deal_breaker_can_name_a_floor(client, listing_provider):
    profile = typical_profile() | {"deal_breakers": ["Energielabel slechter dan C"]}

    case = case_for(client, listing_provider, profile, energy_label="D")

    assert case["hard_no"]["deal_breaker"] == "Energielabel slechter dan C"


def test_an_energielabel_deal_breaker_is_not_hit_by_a_better_label(client, listing_provider):
    profile = typical_profile() | {"deal_breakers": ["Energielabel slechter dan C"]}

    case = case_for(client, listing_provider, profile, energy_label="B")

    assert case["hard_no"] is None
