"""Production Source clients: energielabel from the EP-Online register, WOZ from pyfunda's
third-party (Walter Living) price history. Each fetches for one Listing; nothing bulk-fetches."""

import json
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

from funda.exceptions import FundaRequestError, PriceHistoryError

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
