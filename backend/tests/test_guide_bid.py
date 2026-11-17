import pytest

from app.verdict import GuideBidConfig, derive_guide_bid

CONFIG = GuideBidConfig(
    discount_hoog_ingezet=0.06,
    discount_marktconform=0.025,
    discount_laag_ingezet=0.0,
    band=0.03,
    rounding_step=500,
    long_on_market_days=60,
    discount_long_on_market=0.01,
    very_long_on_market_days=120,
    discount_very_long_on_market=0.02,
    discount_price_reduction=0.01,
    max_discount=0.10,
)


def _tempo(days: int = 10, first_asking_price: int = 600_000, asking_price: int = 600_000) -> dict:
    return {
        "days_on_market": days,
        "first_asking_price": first_asking_price,
        "asking_price": asking_price,
        "price_reduction": first_asking_price > asking_price,
    }


def _case(
    expected: int | None = 600_000,
    asking: int | None = 600_000,
    prijsstelling: str | None = "marktconform",
    *,
    weak: bool = False,
    reserved: bool = False,
    tempo: dict | None = None,
) -> dict:
    return {
        "sold_under_reservation": reserved,
        "metrics": {
            "expected_sale_price": {"value": expected, "weakly_grounded": weak},
            "asking_vs_expected": None
            if prijsstelling is None
            else {"asking_price": asking, "prijsstelling": prijsstelling},
            # A short time on the market at an unchanged asking price adds nothing.
            "market_tempo": tempo if tempo is not None else _tempo(first_asking_price=asking or 0, asking_price=asking or 0),
        },
    }


def _guide(case: dict, maximum: int | None = 700_000):
    return derive_guide_bid(case, maximum, CONFIG)


def test_marktconform_takes_the_marktconform_discount_off_the_expected_sale_price():
    guide = _guide(_case(expected=600_000, asking=610_000))

    assert guide["discount"] == 0.025
    assert guide["value"] == 585_000  # 600.000 * 0,975
    assert guide["breakdown"]["prijsstelling"] == {"prijsstelling": "marktconform", "discount": 0.025}
    assert guide["capped_by"] is None
    assert guide["weakly_grounded"] is False


def test_hoog_ingezet_takes_the_larger_discount():
    guide = _guide(_case(expected=500_000, asking=560_000, prijsstelling="hoog ingezet"))

    assert guide["discount"] == 0.06
    assert guide["value"] == 470_000  # 500.000 * 0,94


def test_laag_ingezet_takes_no_discount_and_opens_above_the_asking_price():
    guide = _guide(_case(expected=600_000, asking=570_000, prijsstelling="laag ingezet"))

    assert guide["discount"] == 0.0
    assert guide["value"] == 600_000
    assert guide["capped_by"] is None


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


@pytest.mark.parametrize(("days", "discount"), [(60, 0.0), (61, 0.01), (120, 0.01), (121, 0.02), (400, 0.02)])
def test_time_on_the_market_adds_to_the_discount_over_60_and_over_120_days(days, discount):
    guide = _guide(_case(expected=600_000, asking=600_000, tempo=_tempo(days=days)))

    assert guide["breakdown"]["days_on_market"] == {"days": days, "discount": discount}
    assert guide["discount"] == pytest.approx(0.025 + discount)


def test_a_price_reduction_adds_a_point():
    tempo = _tempo(days=30, first_asking_price=640_000, asking_price=610_000)
    guide = _guide(_case(expected=600_000, asking=610_000, tempo=tempo))

    assert guide["breakdown"]["price_reduction"] == {
        "reduced": True,
        "first_asking_price": 640_000,
        "asking_price": 610_000,
        "discount": 0.01,
    }
    assert guide["discount"] == pytest.approx(0.035)
    assert guide["value"] == 579_000  # 600.000 * 0,965


def test_no_price_reduction_adds_nothing_and_says_so():
    guide = _guide(_case(tempo=_tempo(days=30)))

    assert guide["breakdown"]["price_reduction"] == {
        "reduced": False,
        "first_asking_price": 600_000,
        "asking_price": 600_000,
        "discount": 0.0,
    }


def test_over_120_days_with_a_price_reduction_adds_three_points():
    tempo = _tempo(days=150, first_asking_price=560_000, asking_price=530_000)
    guide = _guide(_case(expected=500_000, asking=530_000, prijsstelling="hoog ingezet", tempo=tempo))

    assert guide["discount"] == pytest.approx(0.09)  # 6% + 2% + 1%
    assert guide["discount_capped"] is False
    assert guide["value"] == 455_000  # 500.000 * 0,91


def test_the_total_discount_is_capped():
    capped = GuideBidConfig(**{**CONFIG.__dict__, "discount_hoog_ingezet": 0.08})
    tempo = _tempo(days=150, first_asking_price=560_000, asking_price=530_000)
    guide = derive_guide_bid(
        _case(expected=500_000, asking=530_000, prijsstelling="hoog ingezet", tempo=tempo), 700_000, capped
    )

    assert guide["discount"] == 0.10  # 8% + 2% + 1%, capped
    assert guide["discount_capped"] is True
    assert guide["value"] == 450_000


def test_without_a_price_history_the_tempo_does_not_count_and_is_unknown():
    case = _case()
    case["metrics"]["market_tempo"] = None
    guide = _guide(case)

    assert guide["tempo_known"] is False
    assert set(guide["breakdown"]) == {"prijsstelling"}
    assert guide["discount"] == 0.025


def test_with_a_price_history_the_tempo_is_known():
    assert _guide(_case())["tempo_known"] is True
