import pytest

from app.ports import LlmError, SourceFact

from tests.listing_fixtures import LIVE_URL, live_listing
from tests.profile_fixtures import typical_profile

VERDICT = "/api/listings/80907644/verdict"

# The typical household can pay at most 704_519 for the live Listing (asking 595_000, headroom 109_519).
AFFORDABLE_MAXIMUM = 704_519


def model_says(tier="consider", **overrides):
    return {
        "tier": tier,
        "summary": "Degelijke woning, prijs aan de hoge kant.",
        "reasoning": "De woning past bij jullie wensen; de vraagprijs ligt ruim boven de WOZ.",
        "cited_flags": [],
        "bid_advice": {
            "opening_bid": 585_000,
            "walk_away_maximum": 625_000,
            "conditions": ["Financieringsvoorbehoud", "Bouwkundige keuring"],
        },
        **overrides,
    }


def prepare(client, listing_provider, profile=None, **listing_overrides):
    listing_provider.listings[LIVE_URL] = live_listing(**listing_overrides)
    client.post("/api/listings", json={"url": LIVE_URL})
    client.put("/api/buyer-profile", json=profile or typical_profile())


def test_a_verdict_carries_a_tier_reasoning_and_bid_advice(client, listing_provider, llm_client):
    prepare(client, listing_provider)
    llm_client.verdict = model_says("must_buy")

    created = client.post(VERDICT)

    assert created.status_code == 201
    verdict = created.json()
    assert verdict["tier"] == "must_buy"
    assert verdict["reasoning"].startswith("De woning past")
    assert verdict["bid_advice"]["opening_bid"] == 585_000
    assert verdict["bid_advice"]["walk_away_maximum"] == 625_000
    assert verdict["bid_advice"]["affordable_maximum"] == AFFORDABLE_MAXIMUM
    assert verdict["bid_advice"]["conditions"] == ["Financieringsvoorbehoud", "Bouwkundige keuring"]
    assert verdict["deterministic"] is False
    assert client.get(VERDICT).json()["verdicts"] == [verdict]


@pytest.mark.parametrize(
    ("answer", "problem"),
    [
        (model_says("Consider"), "tier_invalid"),
        (model_says("maybe"), "tier_invalid"),
        (model_says(reasoning=""), "reasoning_missing"),
        (model_says(bid_advice=None), "bid_advice_missing"),
        (model_says(cited_flags=["made_up_flag"]), "unknown_flag_cited"),
        (
            model_says(bid_advice={"opening_bid": 600_000, "walk_away_maximum": 590_000, "conditions": []}),
            "opening_bid_above_walk_away_maximum",
        ),
        (
            model_says(
                bid_advice={
                    "opening_bid": 595_000,
                    "walk_away_maximum": AFFORDABLE_MAXIMUM + 1,
                    "conditions": [],
                }
            ),
            "walk_away_maximum_above_affordability",
        ),
        (
            model_says(bid_advice={"opening_bid": "veel", "walk_away_maximum": 600_000, "conditions": []}),
            "bid_advice_invalid",
        ),
        ("not json at all", "not_an_object"),
    ],
)
def test_an_invalid_model_answer_is_rejected_and_reported(
    client, listing_provider, llm_client, answer, problem
):
    prepare(client, listing_provider)
    llm_client.verdict = answer

    response = client.post(VERDICT)

    assert response.status_code == 502
    assert response.json()["code"] == "invalid_verdict"
    assert problem in response.json()["problems"]
    assert client.get(VERDICT).json()["verdicts"] == []


def test_a_walk_away_maximum_exactly_at_affordability_is_accepted(client, listing_provider, llm_client):
    prepare(client, listing_provider)
    llm_client.verdict = model_says(
        bid_advice={"opening_bid": 595_000, "walk_away_maximum": AFFORDABLE_MAXIMUM, "conditions": []}
    )

    assert client.post(VERDICT).status_code == 201


def test_a_skip_needs_no_bid_advice(client, listing_provider, llm_client):
    prepare(client, listing_provider)
    llm_client.verdict = model_says("skip", bid_advice=None)

    verdict = client.post(VERDICT).json()

    assert verdict["tier"] == "skip"
    assert verdict["bid_advice"] is None


def test_a_deal_breaker_hard_no_never_calls_the_llm(client, listing_provider, llm_client):
    profile = typical_profile() | {"deal_breakers": ["Geen erfpacht"]}
    prepare(client, listing_provider, profile, description="Appartement op erfpacht.")

    verdict = client.post(VERDICT).json()

    assert llm_client.rate_calls == []
    assert verdict["tier"] == "hard_no"
    assert verdict["deterministic"] is True
    assert verdict["deal_breaker"] == "Geen erfpacht"
    assert verdict["bid_advice"] is None
    assert verdict["built_from"]["model"] is None
    assert [flag["id"] for flag in verdict["cited_flags"]] == ["deal_breaker_mentioned:Geen erfpacht"]


def test_the_model_sees_the_case_and_reduced_profile_but_no_raw_finances_or_address(
    client, listing_provider, llm_client
):
    profile = typical_profile()
    profile["gross_annual_income"] = 87_654
    profile["assets"] = {"savings": 43_210, "investments": 12_345}
    profile["current_home"]["address"] = "Geheimstraat 9, Utrecht"
    profile["commute_destinations"] = [
        {"label": "Werk", "address": "Kantoorlaan 1, Eindhoven", "max_minutes": 40}
    ]
    profile["must_haves"] = ["Tuin"]
    prepare(client, listing_provider, profile)

    client.post(VERDICT)

    [(case, buyer_profile)] = llm_client.rate_calls
    sent = repr((case, buyer_profile))
    for private in ("87654", "43210", "12345", "Geheimstraat", "Kantoorlaan"):
        assert private not in sent
    assert case["funda_id"] == "80907644"
    assert case["affordability"]["max_price"] > 0
    assert buyer_profile["must_haves"] == ["Tuin"]
    assert buyer_profile["commute_destinations"] == [{"label": "Werk", "max_minutes": 40}]


def test_the_model_is_told_each_facts_provenance(client, listing_provider, source_clients, llm_client):
    source_clients["energielabel"].facts = [SourceFact("energy_label", "A", "2021-06-14")]
    source_clients["woz"].facts = [SourceFact("woz_value", 500_000, "2025-01-01")]
    prepare(client, listing_provider)

    client.post(VERDICT)

    [(case, _)] = llm_client.rate_calls
    legend = case["provenance_legend"]
    for fact in case["facts"]:
        if fact["provenance"] == "source":
            assert f"source:{fact['trust']}" in legend
        else:
            assert fact["provenance"] in legend
    trust = {fact["source"]: fact["trust"] for fact in case["facts"] if fact["provenance"] == "source"}
    assert trust == {"energielabel": "official", "woz": "third_party"}
    assert {"listing", "observation", "finding"} <= set(legend)


def test_cited_flags_are_named_and_bid_advice_shows_monthly_costs(client, listing_provider, llm_client):
    profile = typical_profile() | {"must_haves": ["Tuin"]}
    prepare(client, listing_provider, profile)
    llm_client.verdict = model_says(cited_flags=["must_have_missing:Tuin"])

    verdict = client.post(VERDICT).json()

    assert verdict["cited_flags"] == [
        {"id": "must_have_missing:Tuin", "title": "Must-have ontbreekt: Tuin", "class": "con"}
    ]
    advice = verdict["bid_advice"]
    assert advice["asking_price"] == 595_000
    assert advice["monthly_cost_at_asking_price"] == 1_838
    assert advice["monthly_cost_at_walk_away_maximum"] > advice["monthly_cost_at_asking_price"]


def test_a_verdict_is_versioned_against_case_profile_and_model(client, listing_provider, settings, llm_client):
    prepare(client, listing_provider)
    snapshot_id = client.get("/api/listings/80907644/case").json()["built_from"]["snapshot_id"]
    llm_client.verdict = model_says()

    first = client.post(VERDICT).json()
    second = client.post(VERDICT).json()

    assert first["built_from"]["snapshot_id"] == snapshot_id
    assert first["built_from"]["profile_version"] == 1
    assert first["built_from"]["flag_rules_version"] == 5
    assert first["built_from"]["model"] == settings.verdict_model
    assert (first["version"], second["version"]) == (1, 2)
    state = client.get(VERDICT).json()
    assert [v["version"] for v in state["verdicts"]] == [2, 1]
    assert state["out_of_date"] is False


def test_the_verdict_model_comes_from_configuration(client, listing_provider, settings, llm_client):
    settings.verdict_model = "verdict-model-x"
    settings.vision_model = "vision-model-y"
    prepare(client, listing_provider)
    llm_client.verdict = model_says()

    verdict = client.post(VERDICT).json()

    assert verdict["built_from"]["model"] == "verdict-model-x"
    settings.verdict_model = "verdict-model-z"
    assert client.get(VERDICT).json()["changed"] == ["model"]


def test_editing_the_buyer_profile_marks_verdicts_out_of_date_until_rerun(
    client, listing_provider, llm_client
):
    prepare(client, listing_provider)
    llm_client.verdict = model_says()
    client.post(VERDICT)
    assert client.get("/api/verdicts/out-of-date").json() == {"count": 0, "verdicts": []}

    client.put("/api/buyer-profile", json=typical_profile() | {"renovation_tolerance": 1})

    state = client.get(VERDICT).json()
    assert state["out_of_date"] is True
    assert state["changed"] == ["buyer_profile"]
    stale = client.get("/api/verdicts/out-of-date").json()
    assert stale["count"] == 1
    assert stale["verdicts"][0]["funda_id"] == "80907644"
    assert stale["verdicts"][0]["changed"] == ["buyer_profile"]

    rerun = client.post(VERDICT).json()

    assert rerun["built_from"]["profile_version"] == 2
    assert client.get(VERDICT).json()["out_of_date"] is False
    assert client.get("/api/verdicts/out-of-date").json()["count"] == 0


def test_refetching_a_source_marks_the_verdict_out_of_date(
    client, listing_provider, source_clients, clock, llm_client
):
    source_clients["woz"].facts = [SourceFact("woz_value", 500_000, "2025-01-01")]
    prepare(client, listing_provider)
    llm_client.verdict = model_says()
    client.post(VERDICT)

    clock.advance(days=3)
    client.post("/api/listings/80907644/sources/woz/refetch")

    assert client.get(VERDICT).json()["changed"] == ["case"]


def test_a_failing_model_keeps_the_last_valid_verdict(client, listing_provider, llm_client):
    prepare(client, listing_provider)
    llm_client.verdict = model_says()
    kept = client.post(VERDICT).json()
    llm_client.verdict = LlmError("quota exceeded")

    response = client.post(VERDICT)

    assert response.status_code == 502
    assert response.json() == {"code": "llm_unavailable"}
    assert client.get(VERDICT).json()["verdicts"] == [kept]


def test_a_verdict_needs_a_buyer_profile(client, listing_provider, llm_client):
    listing_provider.listings[LIVE_URL] = live_listing()
    client.post("/api/listings", json={"url": LIVE_URL})

    response = client.post(VERDICT)

    assert response.status_code == 409
    assert response.json() == {"code": "no_buyer_profile"}
    assert llm_client.rate_calls == []


def test_an_unknown_listing_has_no_verdict(client):
    assert client.get("/api/listings/1/verdict").status_code == 404
    assert client.post("/api/listings/1/verdict").status_code == 404


def test_a_manually_entered_listing_gets_a_verdict(client, llm_client):
    client.post(
        "/api/listings/manual",
        data={"url": LIVE_URL, "raw_status": "Beschikbaar", "address": "Buchterweg 15", "asking_price": "595000"},
    )
    client.put("/api/buyer-profile", json=typical_profile())
    llm_client.verdict = model_says()

    verdict = client.post(VERDICT).json()

    assert verdict["tier"] == "consider"
    [(case, _)] = llm_client.rate_calls
    assert {fact["key"]: fact["value"] for fact in case["facts"]}["asking_price"] == 595_000
    assert verdict["bid_advice"]["affordable_maximum"] == case["affordability"]["max_price"]


def test_the_comparison_row_shows_the_latest_verdict_tier(client, listing_provider, llm_client):
    prepare(client, listing_provider)
    assert client.get("/api/listings").json()[0]["comparison"]["tier"] is None

    llm_client.verdict = model_says("consider")
    client.post(VERDICT)
    llm_client.verdict = model_says("must_buy")
    client.post(VERDICT)

    assert client.get("/api/listings").json()[0]["comparison"]["tier"] == "must_buy"


def test_a_case_hard_no_overrides_an_earlier_verdict_tier_in_the_comparison_row(
    client, listing_provider, llm_client
):
    prepare(client, listing_provider, description="Appartement op erfpacht.")
    llm_client.verdict = model_says("must_buy")
    client.post(VERDICT)

    client.put("/api/buyer-profile", json=typical_profile() | {"deal_breakers": ["Geen erfpacht"]})

    row = client.get("/api/listings").json()[0]["comparison"]
    assert (row["tier"], row["hard_no_reason"]) == ("hard_no", "Geen erfpacht")
