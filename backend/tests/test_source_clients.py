import pytest
from funda.exceptions import PriceHistoryError
from funda.listing import PriceChange, PriceHistory

from urllib.parse import parse_qs, urlsplit

from app.ports import SourceFact, SourceFailed, SourceSkipped
from app.source_clients import (
    EpOnlineEnergielabelSource,
    KlimaateffectatlasFloodSoilSource,
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
