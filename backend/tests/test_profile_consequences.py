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
    # 2027 rules (levering 2027-01-24), ten years fixed with NHG at 4,40%: 27,4% of €95.000. The
    # budget: price + 2% + €5.050 + 0,4% NHG fee − €227.000 own funds and equity ≤ the mortgage.
    assert response.json() == {
        "max_mortgage": 433_174,
        "equity": 172_000,
        "budget": 640_586,
        "rules": {
            "version": 2,
            "year": 2027,
            "is_current_year": True,
            "levering_on": "2027-01-24",
            "market_rate_as_of": "2026-11-02",
            "rates": {
                "nhg": {"rate": 0.044, "source": "market", "as_of": "2026-11-02"},
                "no_nhg": {"rate": 0.0478, "source": "market", "as_of": "2026-11-02"},
            },
        },
    }


def test_starters_budget_is_not_reduced_by_transfer_tax(client):
    consequences = client.post("/api/buyer-profile/consequences", json=draft(low_income_profile())).json()

    # 24,1% of €42.000 at 4,40% with NHG; the €12.000 saved covers the fixed costs and NHG fee.
    assert consequences["max_mortgage"] == 168_444
    assert consequences["equity"] == 0
    assert consequences["budget"] == 174_723


def test_blank_balances_and_undated_members_do_not_block_the_figures(client):
    response = client.post(
        "/api/buyer-profile/consequences",
        json={"household": [], "gross_annual_income": 95_000, "assets": {}, "current_home": None},
    )

    assert response.status_code == 200
    assert response.json()["max_mortgage"] == 433_174
    assert response.json()["equity"] == 0


def test_draft_without_income_has_no_figures(client):
    response = client.post("/api/buyer-profile/consequences", json={"household": []})

    assert response.status_code == 422
    assert {"field": "gross_annual_income", "message": "Verplicht veld"} in response.json()["errors"]


def test_rules_from_an_earlier_year_are_reported_as_such(client, settings, tmp_path):
    table = tmp_path / "rules.toml"
    text = settings.affordability_rules_path.read_text()
    table.write_text(text.replace("[years.2026", "[years.2001").replace("[years.2027", "[years.2002"))
    settings.affordability_rules_path = table

    consequences = client.post("/api/buyer-profile/consequences", json=draft(typical_profile())).json()

    assert consequences["rules"]["year"] == 2002
    assert consequences["rules"]["is_current_year"] is False


def test_working_out_consequences_stores_nothing(client):
    client.post("/api/buyer-profile/consequences", json=draft(typical_profile()))

    assert client.get("/api/buyer-profile").status_code == 404


def couple(income: int, **finances) -> dict:
    """Two adults in their fifties (no startersvrijstelling, no alleenstaandenbonus), renting, no savings."""
    return {
        "household": [
            {"role": "adult", "birth_date": "1970-01-01"},
            {"role": "adult", "birth_date": "1971-01-01"},
        ],
        "gross_annual_income": income,
        "assets": {},
        "current_home": None,
        **finances,
    }


def test_short_fixed_rate_period_tests_at_the_toetsrente(client):
    """Nibud, Advies hypotheeknormen 2027, tabel 4: €70.000 at 5% in 2027 (levering falls in 2027)."""
    consequences = client.post(
        "/api/buyer-profile/consequences", json=couple(70_000, fixed_rate_years=5)
    ).json()

    assert consequences["max_mortgage"] == 279_267
    assert consequences["rules"]["year"] == 2027


def with_rules(settings, tmp_path, *replacements: tuple[str, str]) -> None:
    """Point the app at a copy of the affordability rules with some text replaced."""
    text = settings.affordability_rules_path.read_text()
    for old, new in replacements:
        assert old in text
        text = text.replace(old, new)
    table = tmp_path / "rules.toml"
    table.write_text(text)
    settings.affordability_rules_path = table


def offered_rate(settings, tmp_path, rate: str) -> None:
    with_rules(settings, tmp_path, ("nhg = 0.0440", f"nhg = {rate}"), ("no_nhg = 0.0478", f"no_nhg = {rate}"))


def test_long_fixed_rate_period_tests_at_the_offered_rate(client, settings, tmp_path):
    """Nibud, Advies hypotheeknormen 2027, tabel 3: €70.000 and €100.000 at 4,25% in 2027."""
    offered_rate(settings, tmp_path, "0.0425")

    for income, expected in ((70_000, 294_074), (100_000, 467_537)):
        consequences = client.post(
            "/api/buyer-profile/consequences", json=couple(income, fixed_rate_years=10)
        ).json()
        assert consequences["max_mortgage"] == expected


def test_rules_follow_the_year_of_the_expected_levering(client, settings):
    """Nibud tabel 4, 2026 column: €70.000 at 5%. With no months to levering, 2026 rules apply."""
    settings.expected_levering_months = 0

    consequences = client.post(
        "/api/buyer-profile/consequences", json=couple(70_000, fixed_rate_years=5)
    ).json()

    assert consequences["max_mortgage"] == 274_921
    assert consequences["rules"]["year"] == 2026


def test_a_single_adult_may_borrow_the_alleenstaandenbonus_more(client):
    """Trhk 2027 art. 3 lid 8: €18.000 above a toetsinkomen of €31.000, on top of Nibud tabel 4."""
    single = {**couple(70_000, fixed_rate_years=5), "household": [{"role": "adult", "birth_date": "1970-01-01"}]}

    consequences = client.post("/api/buyer-profile/consequences", json=single).json()

    assert consequences["max_mortgage"] == 279_267 + 18_000


def test_other_monthly_debt_lowers_the_maximum_mortgage(client, settings, tmp_path):
    """Nibud advies 2027 §5.1: at 4,25% a study loan of €69,69 a month costs €17.708 of mortgage
    (gross-up 1,25), so €70 a month costs €17.708 × 70 / 69,69 ≈ €17.787."""
    offered_rate(settings, tmp_path, "0.0425")

    consequences = client.post(
        "/api/buyer-profile/consequences", json=couple(70_000, fixed_rate_years=10, other_monthly_debt=70)
    ).json()

    assert consequences["max_mortgage"] == 294_074 - 17_787


def test_kosten_koper_cannot_be_borrowed(client):
    consequences = client.post(
        "/api/buyer-profile/consequences", json=couple(70_000, fixed_rate_years=5)
    ).json()

    assert consequences["budget"] == 0


def test_budget_is_the_highest_price_own_funds_and_the_mortgage_cover(client):
    """€30.000 saved, €279.267 borrowable (tabel 4). Without NHG fee: price + 2% tax + €5.050
    fixed − €30.000 ≤ €279.267 gives €298.252 (tax rounded to the euro)."""
    consequences = client.post(
        "/api/buyer-profile/consequences",
        json=couple(70_000, fixed_rate_years=5, assets={"savings": 30_000, "investments": 0}),
    ).json()

    assert consequences["budget"] == 298_252


def test_without_nhg_a_lender_finances_what_the_nhg_fee_would_tip_over(client):
    """€10.000 saved covers 2% tax and €5.050 fixed costs up to €247.525 (2% is €4.950,50, rounded
    half to even), but not the 0,4% NHG fee on top. A loan without NHG is still within the €279.267
    income norm."""
    consequences = client.post(
        "/api/buyer-profile/consequences",
        json=couple(70_000, fixed_rate_years=5, assets={"savings": 10_000, "investments": 0}),
    ).json()

    assert consequences["budget"] == 247_525


MARKET_NHG = {"rate": 0.044, "source": "market", "as_of": "2026-11-02"}
MARKET_NO_NHG = {"rate": 0.0478, "source": "market", "as_of": "2026-11-02"}


def test_own_nhg_rate_changes_only_the_nhg_route(client):
    """€95.000, ten years fixed. With NHG at an own 5%: 28,4% at 5% gives €418.823, so the route
    without NHG at the market 4,78% (28,4%, €429.516) is the larger one."""
    consequences = client.post(
        "/api/buyer-profile/consequences", json={**draft(typical_profile()), "offered_rate_nhg": 0.05}
    ).json()

    assert consequences["max_mortgage"] == 429_516
    assert consequences["rules"]["rates"] == {
        "nhg": {"rate": 0.05, "source": "own", "as_of": None},
        "no_nhg": MARKET_NO_NHG,
    }


def test_own_rate_without_nhg_changes_only_that_route(client):
    """Without NHG at an own 5% the NHG route at the market 4,40% still gives €433.174."""
    consequences = client.post(
        "/api/buyer-profile/consequences", json={**draft(typical_profile()), "offered_rate_no_nhg": 0.05}
    ).json()

    assert consequences["max_mortgage"] == 433_174
    assert consequences["rules"]["rates"] == {
        "nhg": MARKET_NHG,
        "no_nhg": {"rate": 0.05, "source": "own", "as_of": None},
    }


def test_blank_own_rates_rest_on_the_market_snapshot(client):
    consequences = client.post(
        "/api/buyer-profile/consequences",
        json={**draft(typical_profile()), "offered_rate_nhg": None, "offered_rate_no_nhg": None},
    ).json()

    assert consequences["max_mortgage"] == 433_174
    assert consequences["rules"]["rates"] == {"nhg": MARKET_NHG, "no_nhg": MARKET_NO_NHG}


def test_own_rate_below_the_toetsrente_still_tests_at_it_under_ten_years(client):
    """€70.000, 5 years fixed, own 4%: tested at the 5% toetsrente, Nibud tabel 4's €279.267."""
    consequences = client.post(
        "/api/buyer-profile/consequences",
        json=couple(70_000, fixed_rate_years=5, offered_rate_nhg=0.04, offered_rate_no_nhg=0.04),
    ).json()

    assert consequences["max_mortgage"] == 279_267


def test_own_rate_is_the_test_rate_from_ten_years(client):
    """€70.000, 10 years fixed, own 4%: 23,9% of €70.000 a year (the 3,5-4% column) over 30 years
    at 4% is €1.394,17 a month × 209,46 = €292.024."""
    consequences = client.post(
        "/api/buyer-profile/consequences",
        json=couple(70_000, fixed_rate_years=10, offered_rate_nhg=0.04, offered_rate_no_nhg=0.04),
    ).json()

    assert consequences["max_mortgage"] == 292_024


def test_own_rate_out_of_range_is_rejected(client):
    for rate in (0.004, 0.151):
        response = client.post(
            "/api/buyer-profile/validation", json={**typical_profile(), "offered_rate_nhg": rate}
        )
        assert response.json()["errors"] == [
            {"field": "offered_rate_nhg", "message": "Kies een rente van 0,5% tot en met 15%"}
        ]


def test_own_rate_out_of_range_blocks_the_gevolgen(client):
    response = client.post(
        "/api/buyer-profile/consequences", json={**draft(typical_profile()), "offered_rate_no_nhg": 0.2}
    )

    assert response.status_code == 422
