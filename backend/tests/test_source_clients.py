import pytest
from funda.exceptions import FundaRequestError, ListingNotFound, PriceHistoryError
from funda.listing import (
    Address,
    Areas,
    Listing,
    Price,
    PriceChange,
    PriceHistory,
    PropertyDetails,
    Urls,
)

from urllib.parse import parse_qs, urlsplit

from app.ports import SourceFact, SourceFailed, SourceSkipped
from app.source_clients import (
    EpOnlineEnergielabelSource,
    KlimaateffectatlasFloodSoilSource,
    PyfundaComparablesSource,
    PyfundaWozSource,
    RivmNoiseSource,
)
from tests import pyfunda_fixtures as fx
from tests.listing_fixtures import live_listing

# Shaped like one PandEnergielabelV5 item from the EP-Online v5 API.
EP_ONLINE_LABEL = {
    "Energieklasse": "A",
    "Registratiedatum": "2021-06-14T00:00:00",
    "Opnamedatum": "2021-06-10T00:00:00",
    "Geldig_tot": "2031-06-14T00:00:00",
}


class FakeHttp:
    def __init__(self, status: int, payload: object = None) -> None:
        self.status = status
        self.payload = payload
        self.requests: list[tuple[str, dict]] = []

    def __call__(self, url: str, headers: dict) -> tuple[int, object]:
        self.requests.append((url, headers))
        return self.status, self.payload


def addressed(**overrides):
    return live_listing(postcode="6118 AB", house_number="15", **overrides)


def test_energielabel_is_looked_up_by_postcode_and_house_number():
    http = FakeHttp(200, [EP_ONLINE_LABEL])

    facts = EpOnlineEnergielabelSource("key-1", http).fetch(addressed(house_number_suffix="a"))

    assert facts == [SourceFact(name="energy_label", value="A", as_of="2021-06-14")]
    [(url, headers)] = http.requests
    assert url == (
        "https://public.ep-online.nl/api/v5/PandEnergielabel/Adres"
        "?postcode=6118AB&huisnummer=15&huisletter=a"
    )
    assert headers == {"Authorization": "key-1"}


def test_energielabel_without_a_registered_label_has_no_facts():
    assert EpOnlineEnergielabelSource("key-1", FakeHttp(404)).fetch(addressed()) == []


def test_energielabel_is_skipped_without_api_key_or_address():
    with pytest.raises(SourceSkipped, match="no_api_key"):
        EpOnlineEnergielabelSource(None, FakeHttp(200, [])).fetch(addressed())
    with pytest.raises(SourceSkipped, match="no_address"):
        EpOnlineEnergielabelSource("key-1", FakeHttp(200, [])).fetch(live_listing())


def test_energielabel_register_errors_are_failures():
    with pytest.raises(SourceFailed):
        EpOnlineEnergielabelSource("key-1", FakeHttp(401)).fetch(addressed())


def test_woz_values_come_from_the_price_history():
    history = PriceHistory(
        status="ok",
        changes=(
            PriceChange(price=595000, status="asking_price", date="2026-10-21"),
            PriceChange(price=392000, status="woz", date="2025-01-01"),
            PriceChange(price=371000, status="woz", date="2024-01-01"),
        ),
    )
    client = fx.FakePyfundaClient(fx.live_listing(), history)

    facts = PyfundaWozSource(client).fetch(live_listing())

    assert facts == [
        SourceFact(name="woz_value", value=371000, as_of="2024-01-01"),
        SourceFact(name="woz_value", value=392000, as_of="2025-01-01"),
    ]


def test_unavailable_price_history_is_a_failure():
    client = fx.FakePyfundaClient(fx.live_listing(), history_error=PriceHistoryError("down"))

    with pytest.raises(SourceFailed):
        PyfundaWozSource(client).fetch(live_listing())


def feature_info(properties: dict | None) -> dict:
    """Shaped like a GeoServer WMS GetFeatureInfo response with INFO_FORMAT=application/json."""
    features = [] if properties is None else [{"type": "Feature", "properties": properties}]
    return {"type": "FeatureCollection", "features": features}


class LayerHttp:
    """Answers each WMS GetFeatureInfo request by its QUERY_LAYERS parameter."""

    def __init__(self, payloads: dict[str, dict], status: int = 200) -> None:
        self.payloads = payloads
        self.status = status
        self.queries: list[dict[str, str]] = []

    def __call__(self, url: str, headers: dict) -> tuple[int, object]:
        query = {k: v[0] for k, v in parse_qs(urlsplit(url).query, keep_blank_values=True).items()}
        self.queries.append({"base": url.split("?")[0], **query})
        return self.status, self.payloads.get(query["QUERY_LAYERS"], feature_info(None))


KEA_FLOOD = "maximale_waterdiepte_nederland_kleine_kans_20260128"
KEA_SUBSIDENCE = "nl_bodemdaling_totaal_v20260623"
KEA_PILE_ROT = "risicopaalrot_huidig"


def test_flood_and_soil_risk_are_read_from_the_klimaateffectatlas_at_the_listing():
    http = LayerHttp(
        {
            KEA_FLOOD: feature_info({"GRAY_INDEX": 0.8769000172615051}),
            KEA_SUBSIDENCE: feature_info({"snelheid": -1.50961012304128}),
            KEA_PILE_ROT: feature_info({"buurtnaam": "Holtum", "no_cc_risi": 27.970610687}),
        }
    )

    facts = KlimaateffectatlasFloodSoilSource(http).fetch(
        live_listing(latitude=51.0458, longitude=5.8236)
    )

    assert facts == [
        SourceFact(name="flood_depth_m", value=0.88, as_of="2026-01-28"),
        SourceFact(name="subsidence_mm_per_year", value=1.5, as_of="2026-06-23"),
        SourceFact(name="pile_rot_risk_pct", value=28.0),
    ]
    flood = next(q for q in http.queries if q["QUERY_LAYERS"] == KEA_FLOOD)
    assert flood == {
        "base": "https://cas.cloud.sogelink.com/public/data/org/gws/YWFMLMWERURF/kea_public/wms",
        "SERVICE": "WMS",
        "VERSION": "1.3.0",
        "REQUEST": "GetFeatureInfo",
        "LAYERS": KEA_FLOOD,
        "QUERY_LAYERS": KEA_FLOOD,
        "STYLES": "",
        "CRS": "CRS:84",
        "BBOX": "5.8231,51.0453,5.8241,51.0463",
        "WIDTH": "101",
        "HEIGHT": "101",
        "I": "50",
        "J": "50",
        "INFO_FORMAT": "application/json",
        "FEATURE_COUNT": "1",
    }


def test_an_address_outside_the_flood_scenario_has_zero_flood_depth():
    http = LayerHttp({KEA_FLOOD: feature_info({"GRAY_INDEX": -9999})})

    facts = KlimaateffectatlasFloodSoilSource(http).fetch(live_listing())

    assert facts == [SourceFact(name="flood_depth_m", value=0.0, as_of="2026-01-28")]


def test_flood_soil_is_skipped_without_coordinates_and_fails_on_service_errors():
    with pytest.raises(SourceSkipped, match="no_coordinates"):
        KlimaateffectatlasFloodSoilSource(LayerHttp({})).fetch(live_listing(latitude=None))
    with pytest.raises(SourceFailed, match="http_503"):
        KlimaateffectatlasFloodSoilSource(LayerHttp({}, status=503)).fetch(live_listing())


def test_noise_levels_per_source_are_read_from_the_rivm_noise_maps():
    http = LayerHttp(
        {
            "rivm_20220601_Geluid_lden_allebronnen_2020": feature_info({"GRAY_INDEX": 69}),
            "rivm_20220601_Geluid_lden_wegverkeer_2020": feature_info({"GRAY_INDEX": 64}),
            "rivm_20220601_Geluid_lden_treinverkeer_2020": feature_info({"GRAY_INDEX": 66}),
            "rivm_20220601_Geluid_lden_vliegverkeer_2020": feature_info({"GRAY_INDEX": 0}),
        }
    )

    facts = RivmNoiseSource(http).fetch(live_listing())

    assert facts == [
        SourceFact(name="lden_all_sources_db", value=69, as_of="2020"),
        SourceFact(name="lden_road_db", value=64, as_of="2020"),
        SourceFact(name="lden_rail_db", value=66, as_of="2020"),
    ]
    assert {q["base"] for q in http.queries} == {"https://data.rivm.nl/geo/alo/wms"}
    assert {q["CRS"] for q in http.queries} == {"CRS:84"}


def test_noise_is_skipped_without_coordinates_and_fails_when_unreachable():
    def unreachable(url, headers):
        raise OSError("no route")

    with pytest.raises(SourceSkipped, match="no_coordinates"):
        RivmNoiseSource(LayerHttp({})).fetch(live_listing(longitude=None))
    with pytest.raises(SourceFailed, match="unreachable"):
        RivmNoiseSource(unreachable).fetch(live_listing())


class SimilarPyfunda:
    """Stands in for funda.Funda for comparables: similar-listing ids plus one Listing per id."""

    def __init__(self, sold=(), listed=(), listings=None, similar_error=None):
        self._similar = {"recently_sold": list(sold), "recently_listed": list(listed)}
        self._listings = listings or {}
        self._similar_error = similar_error
        self.listing_calls: list = []

    def similar_listings(self, listing):
        if self._similar_error:
            raise self._similar_error
        return self._similar

    def listing(self, listing_id):
        self.listing_calls.append(listing_id)
        found = self._listings[listing_id]
        if isinstance(found, Exception):
            raise found
        return found

    def search(self, *_args, **_kwargs):
        raise AssertionError("search() must never be called")


def nearby(global_id, price, living, raw_status="Verkocht"):
    return Listing(
        global_id=global_id,
        price=Price(amount=price),
        address=Address(title=f"Dorpsstraat {global_id % 100}", city="Holtum"),
        areas=Areas(living=living),
        property_details=PropertyDetails(raw_status=raw_status),
        urls=Urls(full=f"https://www.funda.nl/detail/koop/holtum/huis-x/{global_id}/"),
    )


def test_comparables_fetch_sold_neighbours_first_and_stop_at_the_cap():
    listings = {i: nearby(i, 500_000 + i, 120) for i in (101, 102, 103, 201, 202)}
    client = SimilarPyfunda(sold=[101, 102, 103], listed=[201, 202], listings=listings)

    facts = PyfundaComparablesSource(client, max_fetches=4).fetch(live_listing())

    assert client.listing_calls == [101, 102, 103, 201]
    assert [f.name for f in facts] == ["comparable"] * 4
    assert facts[0] == SourceFact(
        name="comparable",
        value={
            "funda_id": "101",
            "address": "Dorpsstraat 1",
            "city": "Holtum",
            "asking_price": 500_101,
            "living_area": 120,
            "raw_status": "Verkocht",
            "recently_sold": True,
            "url": "https://www.funda.nl/detail/koop/holtum/huis-x/101/",
        },
    )
    assert facts[3].value["recently_sold"] is False


def test_a_comparable_that_cannot_be_fetched_is_left_out_and_still_counts_against_the_cap():
    client = SimilarPyfunda(
        sold=[101, 102, 103],
        listings={101: ListingNotFound("gone"), 102: nearby(102, 400_000, 100), 103: nearby(103, 1, 1)},
    )

    facts = PyfundaComparablesSource(client, max_fetches=2).fetch(live_listing())

    assert [f.value["funda_id"] for f in facts] == ["102"]


def test_comparables_fail_when_the_similar_listings_lookup_fails():
    client = SimilarPyfunda(similar_error=FundaRequestError("blocked"))

    with pytest.raises(SourceFailed, match="similar_listings_unavailable"):
        PyfundaComparablesSource(client, max_fetches=3).fetch(live_listing())
