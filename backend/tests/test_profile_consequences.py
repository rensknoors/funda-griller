"""Gevolgen: live derived figures for a Buyer Profile draft, before it is saved."""

from tests.profile_fixtures import low_income_profile, typical_profile


def draft(profile: dict) -> dict:
    """The finance vakken of a profile, as the form sends them while editing."""
    return {
        key: profile[key]
        for key in ("household", "gross_annual_income", "assets", "current_home")
        if key in profile
    }


def test_typical_household_sees_maximum_mortgage_equity_and_budget(client):
    response = client.post("/api/buyer-profile/consequences", json=draft(typical_profile()))

    assert response.status_code == 200
    assert response.json() == {
        "max_mortgage": 486_660,
        "equity": 172_000,
        "budget": 694_715,
        "rules": {"year": 2026, "is_current_year": True},
    }


def test_starters_budget_is_not_reduced_by_transfer_tax(client):
    consequences = client.post("/api/buyer-profile/consequences", json=draft(low_income_profile())).json()

    assert consequences["max_mortgage"] == 169_516
    assert consequences["equity"] == 0
    assert consequences["budget"] == 176_466


def test_blank_balances_and_undated_members_do_not_block_the_figures(client):
    response = client.post(
        "/api/buyer-profile/consequences",
        json={"household": [], "gross_annual_income": 95_000, "assets": {}, "current_home": None},
    )

    assert response.status_code == 200
    assert response.json()["max_mortgage"] == 486_660
    assert response.json()["equity"] == 0


def test_draft_without_income_has_no_figures(client):
    response = client.post("/api/buyer-profile/consequences", json={"household": []})

    assert response.status_code == 422
    assert {"field": "gross_annual_income", "message": "Verplicht veld"} in response.json()["errors"]


def test_rules_from_an_earlier_year_are_reported_as_such(client, settings, tmp_path):
    table = tmp_path / "rules.toml"
    table.write_text(settings.affordability_rules_path.read_text().replace("[years.2026", "[years.2001"))
    settings.affordability_rules_path = table

    consequences = client.post("/api/buyer-profile/consequences", json=draft(typical_profile())).json()

    assert consequences["rules"] == {"year": 2001, "is_current_year": False}


def test_working_out_consequences_stores_nothing(client):
    client.post("/api/buyer-profile/consequences", json=draft(typical_profile()))

    assert client.get("/api/buyer-profile").status_code == 404
