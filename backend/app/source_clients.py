"""Production Source clients: energielabel from the EP-Online register, WOZ from pyfunda's
third-party (Walter Living) price history, flood and soil risk from the Klimaateffectatlas and noise
from RIVM's Atlas Leefomgeving. Each fetches for one Listing; nothing bulk-fetches. Also the commute
Source's two ports: PDOK's Locatieserver geocodes destination addresses, OpenRouteService routes."""

import json
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

from funda.exceptions import FundaRequestError, ListingNotFound, PriceHistoryError

from app.ports import Listing, SourceFact, SourceFailed, SourceSkipped

EP_ONLINE_URL = "https://public.ep-online.nl/api/v5/PandEnergielabel/Adres"

HttpGet = Callable[[str, dict], tuple[int, Any]]


def _http_get_json(url: str, headers: dict) -> tuple[int, Any]:
    request = urllib.request.Request(url, headers={**headers, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, None


class EpOnlineEnergielabelSource:
    """Official energielabel register (RVO EP-Online, API v5). Needs an API key and an address."""

    def __init__(self, api_key: str | None, http_get: HttpGet = _http_get_json) -> None:
        self._api_key = api_key
        self._http_get = http_get

    def fetch(self, listing: Listing) -> list[SourceFact]:
        if not self._api_key:
            raise SourceSkipped("no_api_key")
        if not listing.postcode or not listing.house_number:
            raise SourceSkipped("no_address")
        query = {
            "postcode": re.sub(r"\s", "", listing.postcode).upper(),
            "huisnummer": listing.house_number,
        }
        suffix = (listing.house_number_suffix or "").strip(" -")
        if len(suffix) == 1 and suffix.isalpha():
            query["huisletter"] = suffix
        elif suffix:
            query["huisnummertoevoeging"] = suffix
        try:
            status, payload = self._http_get(
                f"{EP_ONLINE_URL}?{urlencode(query)}", {"Authorization": self._api_key}
            )
        except OSError as error:
            raise SourceFailed("unreachable") from error
        if status == 404:
            return []
        if status != 200 or not isinstance(payload, list):
            raise SourceFailed(f"http_{status}")
        labels = [item for item in payload if isinstance(item, dict) and item.get("Energieklasse")]
        if not labels:
            return []
        latest = max(labels, key=lambda item: item.get("Registratiedatum") or "")
        registered = latest.get("Registratiedatum")
        return [
            SourceFact(
                name="energy_label",
                value=latest["Energieklasse"],
                as_of=registered[:10] if registered else None,
            )
        ]


def _coordinates(listing: Listing) -> tuple[float, float]:
    if listing.latitude is None or listing.longitude is None:
        raise SourceSkipped("no_coordinates")
    return listing.longitude, listing.latitude


# Half the side of the box a WMS point query asks about, in degrees (about 50 m); the queried
# pixel is the centre one of 101 x 101, so about 1 m across.
_POINT_BOX = 0.0005


def _point_properties(http_get: HttpGet, wms_url: str, layer: str, lon: float, lat: float) -> dict | None:
    """Properties of the first feature of `layer` at a point, by WMS 1.3.0 GetFeatureInfo with
    CRS:84 (lon/lat axis order), or None when the layer has no feature there."""
    bbox = ",".join(
        str(round(v, 6)) for v in (lon - _POINT_BOX, lat - _POINT_BOX, lon + _POINT_BOX, lat + _POINT_BOX)
    )
    query = {
        "SERVICE": "WMS",
        "VERSION": "1.3.0",
        "REQUEST": "GetFeatureInfo",
        "LAYERS": layer,
        "QUERY_LAYERS": layer,
        "STYLES": "",
        "CRS": "CRS:84",
        "BBOX": bbox,
        "WIDTH": 101,
        "HEIGHT": 101,
        "I": 50,
        "J": 50,
        "INFO_FORMAT": "application/json",
        "FEATURE_COUNT": 1,
    }
    try:
        status, payload = http_get(f"{wms_url}?{urlencode(query)}", {})
    except OSError as error:
        raise SourceFailed("unreachable") from error
    if status != 200 or not isinstance(payload, dict):
        raise SourceFailed(f"http_{status}")
    features = payload.get("features") or []
    return (features[0].get("properties") or {}) if features else None


KEA_WMS_URL = "https://cas.cloud.sogelink.com/public/data/org/gws/YWFMLMWERURF/kea_public/wms"
# Dated layer names: the Klimaateffectatlas publishes new versions under new names.
KEA_FLOOD_LAYER = ("maximale_waterdiepte_nederland_kleine_kans_20260128", "2026-01-28")
KEA_SUBSIDENCE_LAYER = ("nl_bodemdaling_totaal_v20260623", "2026-06-23")
KEA_PILE_ROT_LAYER = "risicopaalrot_huidig"


class KlimaateffectatlasFloodSoilSource:
    """Flood and soil risk at the Listing's coordinates from the Klimaateffectatlas WMS:
    maximum water depth in the small-chance flood scenario (LIWO, metres), total subsidence
    rate (mm a year, positive is sinking) and the buurt's share of buildings at risk of pile rot
    in the current climate (percent)."""

    def __init__(self, http_get: HttpGet = _http_get_json) -> None:
        self._http_get = http_get

    def fetch(self, listing: Listing) -> list[SourceFact]:
        lon, lat = _coordinates(listing)
        facts = []
        flood_layer, flood_as_of = KEA_FLOOD_LAYER
        flood = _point_properties(self._http_get, KEA_WMS_URL, flood_layer, lon, lat)
        if flood is not None and isinstance(flood.get("GRAY_INDEX"), int | float):
            # The raster's no-data (-9999) means no flooding at this point in the scenario.
            depth = max(float(flood["GRAY_INDEX"]), 0.0)
            facts.append(SourceFact("flood_depth_m", round(depth, 2), flood_as_of))
        subsidence_layer, subsidence_as_of = KEA_SUBSIDENCE_LAYER
        subsidence = _point_properties(self._http_get, KEA_WMS_URL, subsidence_layer, lon, lat)
        if subsidence is not None and isinstance(subsidence.get("snelheid"), int | float):
            rate = round(-subsidence["snelheid"], 1)
            facts.append(SourceFact("subsidence_mm_per_year", rate, subsidence_as_of))
        pile_rot = _point_properties(self._http_get, KEA_WMS_URL, KEA_PILE_ROT_LAYER, lon, lat)
        if pile_rot is not None and isinstance(pile_rot.get("no_cc_risi"), int | float):
            facts.append(SourceFact("pile_rot_risk_pct", round(pile_rot["no_cc_risi"], 1)))
        return facts


RIVM_ALO_WMS_URL = "https://data.rivm.nl/geo/alo/wms"
# Atlas Leefomgeving noise maps, Lden in dB for 2020, per kind of source.
RIVM_NOISE_LAYERS = {
    "lden_all_sources_db": "rivm_20220601_Geluid_lden_allebronnen_2020",
    "lden_road_db": "rivm_20220601_Geluid_lden_wegverkeer_2020",
    "lden_rail_db": "rivm_20220601_Geluid_lden_treinverkeer_2020",
    "lden_air_db": "rivm_20220601_Geluid_lden_vliegverkeer_2020",
}
RIVM_NOISE_YEAR = "2020"


class RivmNoiseSource:
    """Noise levels at the Listing's coordinates from RIVM's Atlas Leefomgeving noise maps.
    A level of 0 is the map's no-data value and yields no fact."""

    def __init__(self, http_get: HttpGet = _http_get_json) -> None:
        self._http_get = http_get

    def fetch(self, listing: Listing) -> list[SourceFact]:
        lon, lat = _coordinates(listing)
        facts = []
        for name, layer in RIVM_NOISE_LAYERS.items():
            found = _point_properties(self._http_get, RIVM_ALO_WMS_URL, layer, lon, lat)
            level = found.get("GRAY_INDEX") if found else None
            if isinstance(level, int | float) and level > 0:
                facts.append(SourceFact(name, round(level), RIVM_NOISE_YEAR))
        return facts


PDOK_LOCATIESERVER_URL = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
_POINT = re.compile(r"POINT\(\s*(-?[\d.]+)\s+(-?[\d.]+)\s*\)")


class PdokGeocoder:
    """Commute destination addresses to coordinates through PDOK's Locatieserver: a government
    service needing no account, so the private address goes to no commercial party."""

    def __init__(self, http_get: HttpGet = _http_get_json) -> None:
        self._http_get = http_get

    def geocode(self, address: str) -> tuple[float, float] | None:
        query = {"q": address, "fq": "type:adres", "rows": 1, "fl": "centroide_ll"}
        try:
            status, payload = self._http_get(f"{PDOK_LOCATIESERVER_URL}?{urlencode(query)}", {})
        except OSError as error:
            raise SourceFailed("unreachable") from error
        if status != 200 or not isinstance(payload, dict):
            raise SourceFailed(f"http_{status}")
        docs = (payload.get("response") or {}).get("docs") or []
        match = _POINT.match(str(docs[0].get("centroide_ll", ""))) if docs else None
        if match is None:
            return None
        lon, lat = float(match.group(1)), float(match.group(2))
        return lat, lon


HttpPost = Callable[[str, dict, dict], tuple[int, Any]]


def _http_post_json(url: str, headers: dict, body: dict) -> tuple[int, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        method="POST",
        headers={**headers, "Accept": "application/json", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, None


OPENROUTESERVICE_MATRIX_URL = "https://api.openrouteservice.org/v2/matrix"
# ORS routing profiles per commute mode. ORS has no public transport.
OPENROUTESERVICE_PROFILES = {"car": "driving-car", "bike": "cycling-regular"}


class OpenRouteServiceRouter:
    """Travel times from OpenRouteService's matrix API (HeiGIT, over OpenStreetMap): one request
    per mode for all destinations. Needs an API key (free Standard plan: 500 matrix requests a
    day); only coordinates are sent."""

    def __init__(self, api_key: str | None, http_post: HttpPost = _http_post_json) -> None:
        self._api_key = api_key
        self._http_post = http_post

    def travel_minutes(
        self, origin: tuple[float, float], destinations: list[tuple[float, float]], mode: str
    ) -> list[float | None]:
        if not self._api_key:
            raise SourceSkipped("no_api_key")
        body = {
            "locations": [[lon, lat] for lat, lon in [origin, *destinations]],
            "sources": [0],
            "destinations": list(range(1, len(destinations) + 1)),
            "metrics": ["duration"],
        }
        url = f"{OPENROUTESERVICE_MATRIX_URL}/{OPENROUTESERVICE_PROFILES[mode]}"
        try:
            status, payload = self._http_post(url, {"Authorization": self._api_key}, body)
        except OSError as error:
            raise SourceFailed("unreachable") from error
        durations = payload.get("durations") if isinstance(payload, dict) else None
        if status != 200 or not durations or len(durations[0]) != len(destinations):
            raise SourceFailed(f"http_{status}")
        return [seconds / 60 if isinstance(seconds, int | float) else None for seconds in durations[0]]


class PyfundaWozSource:
    """WOZ values over time from the Listing provider's price-history service. Third-party, not
    an official register; the Case labels it so."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def fetch(self, listing: Listing) -> list[SourceFact]:
        try:
            history = self._client.price_history(listing.funda_id)
        except (PriceHistoryError, FundaRequestError) as error:
            raise SourceFailed("price_history_unavailable") from error
        points = [
            change
            for change in getattr(history, "changes", None) or ()
            if change.status == "woz" and change.price is not None
        ]
        return [
            SourceFact(name="woz_value", value=change.price, as_of=change.date)
            for change in sorted(points, key=lambda change: change.date or "")
        ]


class PyfundaComparablesSource:
    """Nearby comparable Listings from the provider's similar-listings ids. Ids only come back, so
    each comparable is a follow-up fetch: recently sold first, then recently listed, and never more
    than `max_fetches`. Runs only when the user asks; nothing searches or bulk-fetches funda."""

    def __init__(self, client: Any, max_fetches: int) -> None:
        self._client = client
        self._max_fetches = max_fetches

    def fetch(self, listing: Listing) -> list[SourceFact]:
        try:
            similar = self._client.similar_listings(listing.funda_id)
        except (FundaRequestError, ListingNotFound, ValueError) as error:
            raise SourceFailed("similar_listings_unavailable") from error
        candidates = [(gid, True) for gid in similar.get("recently_sold") or ()] + [
            (gid, False) for gid in similar.get("recently_listed") or ()
        ]
        facts = []
        for global_id, recently_sold in candidates[: self._max_fetches]:
            try:
                found = self._client.listing(global_id)
            except (FundaRequestError, ListingNotFound):
                continue
            facts.append(SourceFact(name="comparable", value=_comparable(found, global_id, recently_sold)))
        return facts


def _comparable(found: Any, global_id: object, recently_sold: bool) -> dict:
    address = getattr(found, "address", None)
    details = getattr(found, "property_details", None)
    return {
        "funda_id": str(global_id),
        "address": getattr(address, "title", None),
        "city": getattr(address, "city", None),
        "asking_price": getattr(getattr(found, "price", None), "amount", None),
        "living_area": getattr(getattr(found, "areas", None), "living", None),
        "raw_status": getattr(details, "raw_status", None) or getattr(details, "status", None),
        "recently_sold": recently_sold,
        "url": getattr(getattr(found, "urls", None), "full", None),
    }
