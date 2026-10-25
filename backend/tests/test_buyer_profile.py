import copy

import pytest

VALID_PROFILE = {
    "household": [
        {"role": "adult", "birth_date": "1988-04-12"},
        {"role": "adult", "birth_date": "1990-09-30"},
        {"role": "child", "birth_date": "2020-01-15"},
    ],
    "gross_annual_income": 95_000,
    "assets": {"savings": 40_000, "investments": 15_000},
    "current_home": {
        "value": 400_000,
        "outstanding_mortgage": 220_000,
        "selling_costs": 8_000,
        "address": "Voorbeeldstraat 1, 3511 AB Utrecht",
    },
    "must_haves": ["tuin", "drie slaapkamers"],
    "nice_to_haves": ["garage"],
    "deal_breakers": ["erfpacht"],
    "commute_destinations": [
        {
            "label": "Kantoor",
            "address": "Stationsplein 1, 1012 AB Amsterdam",
            "max_minutes": 45,
        }
    ],
    "renovation_tolerance": 3,
}


@pytest.fixture
def profile():
    return copy.deepcopy(VALID_PROFILE)


def test_no_profile_before_first_save(client):
    assert client.get("/api/buyer-profile").status_code == 404


def test_saved_profile_can_be_read_back(client, profile):
    saved = client.put("/api/buyer-profile", json=profile)

    assert saved.status_code == 200
    assert saved.json()["version"] == 1

    read = client.get("/api/buyer-profile")

    assert read.status_code == 200
    assert read.json()["version"] == 1
    assert read.json()["profile"] == profile


def test_each_save_creates_a_new_version_and_keeps_earlier_ones(client, profile):
    client.put("/api/buyer-profile", json=profile)
    edited = copy.deepcopy(profile)
    edited["gross_annual_income"] = 105_000
    saved = client.put("/api/buyer-profile", json=edited)

    assert saved.json()["version"] == 2
    assert client.get("/api/buyer-profile").json()["profile"] == edited

    versions = client.get("/api/buyer-profile/versions").json()

    assert [v["version"] for v in versions] == [2, 1]
    assert versions[1]["profile"]["gross_annual_income"] == 95_000
    assert versions[0]["profile"]["gross_annual_income"] == 105_000


def test_saving_identical_profile_still_creates_a_version(client, profile):
    client.put("/api/buyer-profile", json=profile)

    assert client.put("/api/buyer-profile", json=profile).json()["version"] == 2


def _set(path, value):
    def mutate(profile):
        target = profile
        *parents, last = path.split(".")
        for key in parents:
            target = target[int(key)] if key.isdigit() else target[key]
        if last.isdigit():
            target[int(last)] = value
        else:
            target[last] = value

    return mutate


def _remove(key):
    return lambda profile: profile.pop(key)


NO_ADDRESS = "Geen adres of postcode: deze tekst gaat mee naar het taalmodel"

INVALID_INPUT = [
    ("negative income", _set("gross_annual_income", -1), "gross_annual_income", "Bedrag buiten bereik"),
    ("absurd income", _set("gross_annual_income", 50_000_000), "gross_annual_income", "Bedrag buiten bereik"),
    ("negative savings", _set("assets.savings", -5), "assets.savings", "Bedrag buiten bereik"),
    ("negative home value", _set("current_home.value", -1), "current_home.value", "Bedrag buiten bereik"),
    (
        "mortgage above home value",
        _set("current_home.outstanding_mortgage", 500_000),
        "current_home.outstanding_mortgage",
        "Hypotheek is hoger dan de woningwaarde",
    ),
    ("birth date in the future", _set("household.0.birth_date", "2999-01-01"), "household.0.birth_date", "Geboortedatum ligt in de toekomst"),
    ("impossible birth date", _set("household.0.birth_date", "1988-02-31"), "household.0.birth_date", "Ongeldige datum"),
    ("birth date long ago", _set("household.0.birth_date", "1850-01-01"), "household.0.birth_date", "Geboortedatum is niet geloofwaardig"),
    ("no household", _set("household", []), "household", "Voeg minstens één volwassene toe"),
    ("only children", _set("household", [{"role": "child", "birth_date": "2020-01-15"}]), "household", "Voeg minstens één volwassene toe"),
    ("missing income", _remove("gross_annual_income"), "gross_annual_income", "Verplicht veld"),
    ("blank must-have", _set("must_haves", ["  "]), "must_haves.0", "Verplicht veld"),
    ("blank commute label", _set("commute_destinations.0.label", ""), "commute_destinations.0.label", "Verplicht veld"),
    ("zero commute minutes", _set("commute_destinations.0.max_minutes", 0), "commute_destinations.0.max_minutes", "Bedrag buiten bereik"),
    ("tolerance too high", _set("renovation_tolerance", 6), "renovation_tolerance", "Kies een waarde van 1 tot en met 5"),
    ("tolerance missing", _remove("renovation_tolerance"), "renovation_tolerance", "Verplicht veld"),
    ("postcode in a must-have", _set("must_haves.0", "dichtbij 3511 AB"), "must_haves.0", NO_ADDRESS),
    ("postcode in a nice-to-have", _set("nice_to_haves.0", "rond 1012ab"), "nice_to_haves.0", NO_ADDRESS),
    ("street address in a deal-breaker", _set("deal_breakers.0", "verder dan Dorpsstraat 12"), "deal_breakers.0", NO_ADDRESS),
    ("street address in a commute label", _set("commute_destinations.0.label", "Kerkplein 4"), "commute_destinations.0.label", NO_ADDRESS),
]


@pytest.mark.parametrize(
    ("mutate", "field", "message"),
    [case[1:] for case in INVALID_INPUT],
    ids=[case[0] for case in INVALID_INPUT],
)
def test_invalid_input_is_rejected_with_a_clear_message(client, profile, mutate, field, message):
    mutate(profile)

    response = client.put("/api/buyer-profile", json=profile)

    assert response.status_code == 422
    assert {"field": field, "message": message} in response.json()["errors"]


def test_a_draft_can_be_checked_without_saving(client, profile):
    profile["gross_annual_income"] = -1
    del profile["renovation_tolerance"]

    response = client.post("/api/buyer-profile/validation", json=profile)

    assert response.status_code == 200
    assert sorted(response.json()["errors"], key=lambda e: e["field"]) == [
        {"field": "gross_annual_income", "message": "Bedrag buiten bereik"},
        {"field": "renovation_tolerance", "message": "Verplicht veld"},
    ]
    assert client.get("/api/buyer-profile").status_code == 404


def test_a_valid_draft_has_no_problems(client, profile):
    response = client.post("/api/buyer-profile/validation", json=profile)

    assert response.json() == {"errors": []}
    assert client.get("/api/buyer-profile").status_code == 404


def test_preferences_that_merely_mention_numbers_are_accepted(client, profile):
    profile["must_haves"] = ["bouwjaar na 1930 en tuin", "minstens 3 slaapkamers"]
    profile["deal_breakers"] = ["aan een drukke weg"]

    assert client.put("/api/buyer-profile", json=profile).status_code == 200


def test_rejected_profile_is_not_stored(client, profile):
    client.put("/api/buyer-profile", json=profile)
    profile["gross_annual_income"] = -1
    client.put("/api/buyer-profile", json=profile)

    assert [v["version"] for v in client.get("/api/buyer-profile/versions").json()] == [1]


def test_reduced_profile_has_derived_figures_and_preferences_only(client, profile):
    client.put("/api/buyer-profile", json=profile)

    response = client.get("/api/buyer-profile/reduced")

    assert response.status_code == 200
    assert response.json() == {
        "profile_version": 1,
        "household": {"adults": 2, "children": 1},
        "home_equity": 172_000,
        "renovation_tolerance": 3,
        "must_haves": ["tuin", "drie slaapkamers"],
        "nice_to_haves": ["garage"],
        "deal_breakers": ["erfpacht"],
        "commute_destinations": [{"label": "Kantoor", "max_minutes": 45}],
    }


def test_reduced_profile_leaks_no_raw_income_balances_or_addresses(client, profile):
    client.put("/api/buyer-profile", json=profile)

    body = client.get("/api/buyer-profile/reduced").text

    for secret in ("95000", "40000", "15000", "400000", "220000", "8000", "Voorbeeldstraat", "Stationsplein", "1988"):
        assert secret not in body


def test_reduced_profile_without_a_current_home_has_no_equity(client, profile):
    profile["current_home"] = None
    client.put("/api/buyer-profile", json=profile)

    assert client.get("/api/buyer-profile/reduced").json()["home_equity"] == 0


def test_reduced_profile_follows_the_latest_version(client, profile):
    client.put("/api/buyer-profile", json=profile)
    profile["current_home"]["value"] = 450_000
    client.put("/api/buyer-profile", json=profile)

    reduced = client.get("/api/buyer-profile/reduced").json()

    assert reduced["profile_version"] == 2
    assert reduced["home_equity"] == 222_000


def test_no_reduced_profile_before_first_save(client):
    assert client.get("/api/buyer-profile/reduced").status_code == 404


def test_profile_endpoints_make_no_llm_call(client, profile, llm_client):
    client.put("/api/buyer-profile", json=profile)
    client.get("/api/buyer-profile")
    client.get("/api/buyer-profile/versions")
    client.get("/api/buyer-profile/reduced")

    assert llm_client.rate_calls == []


def test_reading_a_buyer_profile_before_one_is_saved_says_so_in_the_common_error_shape(client):
    for path in ("/api/buyer-profile", "/api/buyer-profile/reduced"):
        response = client.get(path)

        assert (response.status_code, response.json()) == (404, {"code": "no_buyer_profile"})
