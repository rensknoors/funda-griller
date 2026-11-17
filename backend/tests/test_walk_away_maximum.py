from app.verdict import derive_walk_away_maximum

PREMIUM = 0.05


def _case(expected: int | None, *, weak: bool = False, affordable: int = 900_000, direct: int = 6_000) -> dict:
    return {
        "affordability": {"affordable_maximum": affordable},
        "renovation_estimate": {"direct_midpoint": direct},
        "metrics": {
            "expected_sale_price": {
                "value": expected,
                "basis": None if expected is None else "woz" if weak else "comparables",
                "weakly_grounded": None if expected is None else weak,
            }
        },
    }


def test_a_strong_expected_sale_price_less_direct_nodig_plus_the_premium_is_the_maximum():
    derivation = derive_walk_away_maximum(_case(600_000), PREMIUM)

    assert derivation["walk_away_maximum"] == 623_700  # (600.000 - 6.000) * 1,05
    assert derivation["basis_maximum"] == 623_700
    assert derivation["premium"] == PREMIUM
    assert derivation["binding"] == "basis"
    assert derivation["weakly_grounded"] is False


def test_a_weak_expected_sale_price_makes_the_maximum_weakly_grounded():
    derivation = derive_walk_away_maximum(_case(600_000, weak=True), PREMIUM)

    assert derivation["walk_away_maximum"] == 623_700
    assert derivation["weakly_grounded"] is True


def test_affordability_binds_when_it_is_lower_than_the_basis_maximum():
    derivation = derive_walk_away_maximum(_case(600_000, affordable=610_000), PREMIUM)

    assert derivation["walk_away_maximum"] == 610_000
    assert derivation["basis_maximum"] == 623_700
    assert derivation["binding"] == "affordability"


def test_without_an_expected_sale_price_there_is_no_maximum():
    derivation = derive_walk_away_maximum(_case(None), PREMIUM)

    assert derivation["walk_away_maximum"] is None
    assert derivation["basis_maximum"] is None
    assert derivation["weakly_grounded"] is None
