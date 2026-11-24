"""App wired to fakes and a temp SQLite file, served to the Playwright smoke test."""

import base64
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.case import DUTCH_MONTHS
from app.main import create_app
from app.ports import Ports, PricePoint, ProviderBlocked, SourceFact, SourceSkipped
from app.settings import Settings
from tests.conftest import SOURCES
from tests.fakes import (
    FakeDocumentDownloader,
    FakeGeocoder,
    FakeListingProvider,
    FakeLlmClient,
    FakePhotoDownloader,
    FakeSourceClient,
    FakeTravelTimeRouter,
)
from tests.listing_fixtures import LIVE_URL, live_listing
from tests.pdf_fixtures import make_pdf

BLOCKED_URL = "https://www.funda.nl/detail/koop/utrecht/huis-oudegracht-2/12345678/"
# Available on first fetch, sold on every refetch after: the comparison view's status change.
CHANGING_URL = "https://www.funda.nl/detail/koop/maastricht/appartement-markt-3/55500001/"

_data_dir = Path(tempfile.mkdtemp(prefix="funda-griller-e2e-"))

_listing_provider = FakeListingProvider()
_listing_provider.listings[LIVE_URL] = live_listing()
_listing_provider.listings[BLOCKED_URL] = ProviderBlocked(BLOCKED_URL)
# Its own woning, so fetching comparables and an Oordeel here leaves the other specs' woning alone.
COMPARABLES_URL = "https://www.funda.nl/detail/koop/holtum/huis-dorpsstraat-40/80907650/"
_listing_provider.listings[COMPARABLES_URL] = live_listing(
    funda_id="80907650", provider_id="17270380", url=COMPARABLES_URL, address="Dorpsstraat 40"
)
_markt = dict(
    funda_id="55500001",
    provider_id="55500001",
    url=CHANGING_URL,
    address="Markt 3",
    city="Maastricht",
    asking_price=425_000,
    living_area=80,
    plot_area=None,
    rooms=3,
    bedrooms=2,
    construction_year=1965,
    energy_label="C",
    description="Appartement met balkon.",
    price_history=(),
    photo_urls=(),
    brochure_url=None,
)
_listing_provider.listings[CHANGING_URL] = [
    live_listing(**_markt),
    live_listing(**_markt, raw_status="Verkocht"),
]

# Its own woning for the Richtbod spec. No price history, so its tempo is unknown.
GUIDE_BID_URL = "https://www.funda.nl/detail/koop/holtum/huis-kerkpad-2/80907660/"
_listing_provider.listings[GUIDE_BID_URL] = live_listing(
    funda_id="80907660", provider_id="17270390", url=GUIDE_BID_URL, address="Kerkpad 2", price_history=()
)
# Listed 130 days before today (the e2e app runs on the real clock) at 625.000, now asking 595.000:
# over 120 days on the market with a price reduction.
TEMPO_URL = "https://www.funda.nl/detail/koop/holtum/huis-kerkpad-4/80907661/"
# UTC, like the snapshot's fetch time.
_listed = datetime.now(UTC).date() - timedelta(days=130)
_listing_provider.listings[TEMPO_URL] = live_listing(
    funda_id="80907661",
    provider_id="17270391",
    url=TEMPO_URL,
    address="Kerkpad 4",
    price_history=(PricePoint(date=f"{_listed.day} {DUTCH_MONTHS[_listed.month - 1]} {_listed.year}", price=625_000),),
)
# Its own woning for the Notitie spec, so its Achterhaald Oordeel leaves the other specs' alone.
NOTE_URL = "https://www.funda.nl/detail/koop/holtum/huis-kerkpad-6/80907662/"
_listing_provider.listings[NOTE_URL] = live_listing(
    funda_id="80907662", provider_id="17270392", url=NOTE_URL, address="Kerkpad 6"
)
# Verkocht onder voorbehoud: its Oordeel gives conditions only (no Openingsbod or Richtbod).
RESERVED_URL = "https://www.funda.nl/detail/koop/maastricht/appartement-molenstraat-7/55500002/"
_listing_provider.listings[RESERVED_URL] = live_listing(
    **{**_markt, "funda_id": "55500002", "provider_id": "55500002", "url": RESERVED_URL, "address": "Molenstraat 7"},
    raw_status="Verkocht onder voorbehoud",
)
# Its own woning for the flags spec, whose Harde afwijzing needs fetched comparables (a strongly
# grounded Expected Sale Price) there, so the other specs' woningen keep theirs as they are.
STRONG_URL = "https://www.funda.nl/detail/koop/holtum/huis-hoogstraat-8/80907658/"
_listing_provider.listings[STRONG_URL] = live_listing(
    funda_id="80907658", provider_id="17270388", url=STRONG_URL, address="Hoogstraat 8"
)
# For the Verwachte verkoopprijs spec: one woning without any WOZ-waarde (no Expected Sale Price
# until comparables are fetched) and one with a much lower WOZ-waarde (more headroom).
NO_WOZ_URL = "https://www.funda.nl/detail/koop/holtum/huis-hoogstraat-7/80907657/"
_listing_provider.listings[NO_WOZ_URL] = live_listing(
    funda_id="80907657", provider_id="17270387", url=NO_WOZ_URL, address="Hoogstraat 7"
)
LOW_WOZ_URL = "https://www.funda.nl/detail/koop/holtum/huis-hoogstraat-9/80907659/"
_listing_provider.listings[LOW_WOZ_URL] = live_listing(
    funda_id="80907659", provider_id="17270389", url=LOW_WOZ_URL, address="Hoogstraat 9"
)
# For the Correctie spec: one woning to correct, and one whose woonoppervlak the advertentie changes
# from 128 to 120 m² on the refetch after the first, with no perceeloppervlak stated.
CORRECTION_URL = "https://www.funda.nl/detail/koop/holtum/huis-kerkpad-10/80907663/"
_listing_provider.listings[CORRECTION_URL] = live_listing(
    funda_id="80907663", provider_id="17270393", url=CORRECTION_URL, address="Kerkpad 10"
)
RECAPTURE_URL = "https://www.funda.nl/detail/koop/holtum/huis-kerkpad-12/80907664/"
_kerkpad_12 = dict(funda_id="80907664", provider_id="17270394", url=RECAPTURE_URL, address="Kerkpad 12", plot_area=None)
_listing_provider.listings[RECAPTURE_URL] = [
    live_listing(**_kerkpad_12, living_area=128),
    live_listing(**_kerkpad_12, living_area=120),
]


class _WozClient(FakeSourceClient):
    """The same WOZ-waarde for every woning, except the two that exercise the Expected Sale Price."""

    def fetch(self, listing):
        if listing.funda_id == "80907657":
            return []
        if listing.funda_id == "80907659":
            return [SourceFact("woz_value", 300_000, "2025-01-01")]
        return super().fetch(listing)


_source_clients = {name: FakeSourceClient(name) for name in SOURCES}
_source_clients["woz"] = _WozClient("woz")
_source_clients["energielabel"].facts = [SourceFact("energy_label", "A", "2021-06-14")]
_source_clients["woz"].facts = [
    SourceFact("woz_value", 371_000, "2024-01-01"),
    SourceFact("woz_value", 392_000, "2025-01-01"),
]
_source_clients["flood_soil"].facts = [
    SourceFact("flood_depth_m", 0.88, "2026-01-28"),
    SourceFact("subsidence_mm_per_year", 1.5, "2026-06-23"),
    SourceFact("pile_rot_risk_pct", 2.1),
]
_source_clients["noise"].error = SourceSkipped("no_coordinates")
# Fetched only when the user asks. Per m²: 4000, 4200, 4400, 4200, 4200 -> median 4200.
_source_clients["comparables"].facts = [
    SourceFact(
        "comparable",
        {
            "funda_id": funda_id,
            "address": address,
            "city": "Holtum",
            "asking_price": price,
            "living_area": area,
            "raw_status": "Verkocht",
            "recently_sold": True,
            "url": f"https://www.funda.nl/detail/koop/holtum/huis/{funda_id}/",
        },
    )
    for funda_id, address, price, area in (
        ("80900001", "Dorpsstraat 3", 500_000, 125),
        ("80900002", "Kerkstraat 8", 630_000, 150),
        ("80900003", "Molenweg 21", 550_000, 125),
        ("80900004", "Beekstraat 5", 420_000, 100),
        ("80900005", "Lindelaan 9", 462_000, 110),
    )
]


def _rate(case: dict, _profile: dict) -> dict:
    """A plausible Verdict derived from the Case, so it always passes validation."""
    asking = next(f["value"] for f in case["facts"] if f["key"] == "asking_price")
    affordable = case["affordability"]["affordable_maximum"]
    cited = [flag["id"] for flag in case["flags"]]
    if affordable < asking:
        return {
            "tier": "skip",
            "summary": "Buiten je betaalruimte.",
            "reasoning": "De vraagprijs ligt boven wat jullie kunnen betalen.",
            "cited_flags": cited,
            "bid_advice": None,
        }
    walk_away = case["walk_away"]["walk_away_maximum"]
    if walk_away is None:
        # No Expected Sale Price: the price cannot be judged, so conditions only.
        return {
            "tier": "consider",
            "summary": "De prijs is niet te beoordelen.",
            "reasoning": "Zonder verwachte verkoopprijs valt niet te zeggen wat de woning waard is.",
            "cited_flags": cited,
            "bid_advice": {"opening_bid": None, "conditions": ["Financieringsvoorbehoud", "Bouwkundige keuring"]},
        }
    guide_bid = case["guide_bid"]
    if case["sold_under_reservation"]:
        advice = {"conditions": ["Reserveringslijst opvragen"]}
    elif guide_bid:
        # A little above the Guide Bid (above the asking price too when laag ingezet): inside the band,
        # so the Richtbod shows next to the Openingsbod with the reason.
        advice = {
            "opening_bid": min(walk_away, guide_bid["value"] + 1_000),
            "deviation_reason": "Vocht in de kelder.",
            "conditions": ["Financieringsvoorbehoud", "Bouwkundige keuring"],
        }
    else:
        advice = {
            "opening_bid": min(walk_away, asking - 15_000),
            "conditions": ["Financieringsvoorbehoud", "Bouwkundige keuring"],
        }
    return {
        "tier": "consider",
        "summary": "Degelijke woning, de vraagprijs is aan de hoge kant.",
        "reasoning": "De woning past bij jullie wensen, maar de vraagprijs ligt ver boven de "
        "WOZ-waarde. Die WOZ komt van een derde partij en is onofficieel.",
        "cited_flags": cited,
        "bid_advice": advice,
    }


def _findings(document_path: str) -> list[dict]:
    """Findings keyed off the generated PDFs' text: the Vragenlijst discloses asbestos, the
    brochure says what stays."""
    content = Path(document_path).read_bytes()
    if b"asbest" in content:
        return [
            {
                "topic": "asbestos",
                "present": True,
                "statement": "Asbest in de dakplaten van de schuur.",
                "quote": "Ja, in de dakplaten van de schuur.",
                "page": 2,
            }
        ]
    if b"Brochure" in content:
        return [
            {
                "topic": "stays_or_goes",
                "present": True,
                "statement": "De gordijnen blijven achter.",
                "quote": "De gordijnen blijven achter.",
                "page": 2,
            }
        ]
    return []


_llm_client = FakeLlmClient()
_llm_client.verdict = _rate
_llm_client.findings = _findings
_document_downloader = FakeDocumentDownloader(make_pdf(["Brochure Buchterweg 15", "De gordijnen blijven achter."]))
# Observations that raise no Flag, so the other specs' Signaal counts stay as they are.
_llm_client.observations = [
    {"key": "kitchen_age_years", "value": 12, "photos": [2], "note": "Lichte keuken met moderne fronten"},
    {"key": "roof_condition", "value": "fair", "photos": [1], "note": "Dakpannen deels verkleurd"},
]

# A 1x1 PNG for every Listing photo, so the browser renders real images.
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
_photo_downloader = FakePhotoDownloader()
_photo_downloader.photos = {url: _PNG for url in live_listing().photo_urls}

# Commute: one office, 52 minutes by car and 140 by bike from any woning. Only profiles with a
# commute destination run it; the other specs' profiles have none, so it is skipped there.
_geocoder = FakeGeocoder()
_geocoder.places = {"Kantoorlaan 1, Eindhoven": (51.44, 5.47)}
_router = FakeTravelTimeRouter()
_router.minutes = {("car", (51.44, 5.47)): 52.0, ("bike", (51.44, 5.47)): 140.0}
# Its own woning, so the commute spec's Signaal leaves the other specs' counts alone.
COMMUTE_URL = "https://www.funda.nl/detail/koop/holtum/huis-dorpsstraat-41/80907651/"
_listing_provider.listings[COMMUTE_URL] = live_listing(
    funda_id="80907651", provider_id="17270381", url=COMMUTE_URL, address="Dorpsstraat 41"
)

# Its own woning for the Verbouwingsraming spec, so its uploaded Vragenlijst (asbestos: Direct nodig)
# leaves the other specs' figures alone.
RENOVATION_URL = "https://www.funda.nl/detail/koop/holtum/huis-dorpsstraat-42/80907652/"
_listing_provider.listings[RENOVATION_URL] = live_listing(
    funda_id="80907652", provider_id="17270382", url=RENOVATION_URL, address="Dorpsstraat 42"
)

# Its own woning for the capture progress spec, captured fresh by that spec.
PROGRESS_URL = "https://www.funda.nl/detail/koop/holtum/huis-dorpsstraat-43/80907653/"
_listing_provider.listings[PROGRESS_URL] = live_listing(
    funda_id="80907653", provider_id="17270383", url=PROGRESS_URL, address="Dorpsstraat 43"
)

app = create_app(
    Settings(
        _env_file=None,
        database_path=_data_dir / "e2e.sqlite",
        media_dir=_data_dir / "media",
    ),
    Ports(
        listing_provider=_listing_provider,
        source_clients=_source_clients,
        llm_client=_llm_client,
        photo_downloader=_photo_downloader,
        document_downloader=_document_downloader,
        geocoder=_geocoder,
        router=_router,
    ),
)
