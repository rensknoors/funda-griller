import pytest

from app.verdict import GuideBidConfig, derive_guide_bid

CONFIG = GuideBidConfig(
    discount_hoog_ingezet=0.06,
    discount_marktconform=0.025,
    discount_laag_ingezet=0.0,
    band=0.03,
    rounding_step=500,
)


def _case(
    expected: int | None = 600_000,
    asking: int | None = 600_000,
    prijsstelling: str | None = "marktconform",
    *,
    weak: bool = False,
    reserved: bool = False,
) -> dict:
    return {
        "sold_under_reservation": reserved,
        "metrics": {
            "expected_sale_price": {"value": expected, "weakly_grounded": weak},
            "asking_vs_expected": None
            if prijsstelling is None
            else {"asking_price": asking, "prijsstelling": prijsstelling},
        },
    }


def _guide(case: dict, maximum: int | None = 700_000):
    return derive_guide_bid(case, maximum, CONFIG)


def test_marktconform_takes_the_marktconform_discount_off_the_expected_sale_price():
    guide = _guide(_case(expected=600_000, asking=610_000))

    assert guide["discount"] == 0.025
    assert guide["value"] == 585_000  # 600.000 * 0,975
    assert guide["breakdown"]["prijsstelling"] == {"label": "marktconform", "discount": 0.025}
    assert guide["capped_by"] is None
    assert guide["weakly_grounded"] is False


def test_hoog_ingezet_takes_the_larger_discount():
    guide = _guide(_case(expected=500_000, asking=560_000, prijsstelling="hoog ingezet"))

    assert guide["discount"] == 0.06
    assert guide["value"] == 470_000  # 500.000 * 0,94


def test_laag_ingezet_takes_no_discount_but_never_goes_above_the_asking_price():
    guide = _guide(_case(expected=600_000, asking=570_000, prijsstelling="laag ingezet"))

    assert guide["discount"] == 0.0
    assert guide["value"] == 570_000
    assert guide["capped_by"] == "asking_price"


def test_the_walk_away_maximum_caps_the_guide_bid():
    guide = _guide(_case(expected=600_000, asking=610_000), maximum=580_000)

    assert guide["value"] == 580_000
    assert guide["capped_by"] == "walk_away_maximum"


@pytest.mark.parametrize(("expected", "value"), [(603_000, 587_500), (603_400, 588_000), (603_600, 588_500)])
def test_the_guide_bid_is_rounded_down_to_the_step(expected, value):
    # 603.000 * 0,975 = 587.925; 603.400 * 0,975 = 588.315; 603.600 * 0,975 = 588.510
    assert _guide(_case(expected=expected, asking=expected))["value"] == value


def test_a_weakly_grounded_expected_sale_price_gets_the_same_discount_and_is_flagged():
    guide = _guide(_case(weak=True))

    assert guide["discount"] == 0.025
    assert guide["weakly_grounded"] is True


def test_the_band_is_part_of_the_guide_bid():
    assert _guide(_case())["band"] == 0.03


@pytest.mark.parametrize(
    "case",
    [_case(expected=None, prijsstelling=None), _case(asking=None, prijsstelling=None), _case(reserved=True)],
    ids=["no expected sale price", "no asking price", "sold under reservation"],
)
def test_there_is_no_guide_bid_without_its_basis_or_for_a_house_sold_under_reservation(case):
    assert _guide(case) is None


def test_there_is_no_guide_bid_without_a_walk_away_maximum():
    assert _guide(_case(), maximum=None) is None
