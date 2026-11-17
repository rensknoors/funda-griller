"""Time on the market in the Case (ADR-0005): days from the current listing's first price_history
date to the snapshot's fetch date, and whether its first asking price was above the current one."""

import pytest

from app.ports import PricePoint

from tests.listing_fixtures import LIVE_URL, live_listing
from tests.test_comparables_api import NOW

CASE = "/api/listings/80907644/case"


def market_tempo(client, listing_provider, **overrides):
    listing_provider.listings[LIVE_URL] = live_listing(**overrides)
    client.post("/api/listings", json={"url": LIVE_URL})
    return client.get(CASE).json()["metrics"]["market_tempo"]


def test_days_on_the_market_run_from_the_first_price_history_date_to_the_fetch_date(client, listing_provider):
    # Fetched 2026-10-24: funda's "15 apr 2026" is 192 days earlier; the earlier sale does not count.
    tempo = market_tempo(
        client,
        listing_provider,
        asking_price=795_000,
        price_history=(PricePoint(date="15 apr 2026", price=819_500), PricePoint(date="4 jan 2023", price=375_000)),
    )

    assert tempo == {
        "listed_on": "2026-04-15",
        "days_on_market": 192,
        "first_asking_price": 819_500,
        "asking_price": 795_000,
        "price_reduction": True,
        "provenance": "computed",
        "computed_at": NOW,
    }


@pytest.mark.parametrize(
    ("date", "days"), [("2026-10-21", 3), ("1 mrt 2026", 237), ("31 okt 2025", 358), ("24 okt 2026", 0)]
)
def test_dates_are_read_in_funda_and_iso_form(client, listing_provider, date, days):
    tempo = market_tempo(client, listing_provider, price_history=(PricePoint(date=date, price=595_000),))

    assert tempo["days_on_market"] == days
    assert tempo["price_reduction"] is False


@pytest.mark.parametrize(
    "history",
    [(), (PricePoint(date=None, price=595_000),), (PricePoint(date="ergens in mei", price=595_000),)],
    ids=["empty", "no date", "unreadable date"],
)
def test_without_a_readable_price_history_the_tempo_is_unknown(client, listing_provider, history):
    assert market_tempo(client, listing_provider, price_history=history) is None


def test_a_first_price_at_or_below_the_asking_price_is_no_reduction(client, listing_provider):
    tempo = market_tempo(
        client, listing_provider, asking_price=600_000, price_history=(PricePoint(date="2026-10-01", price=575_000),)
    )

    assert tempo["price_reduction"] is False
