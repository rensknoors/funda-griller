import re

from app.ports import InvalidListingUrl

_DETAIL_URL = re.compile(
    r"^https?://(?:www\.)?funda\.nl/(?:[\w-]+/)*?(?:detail/koop/)(?:[\w-]+/)*?(\d{7,9})/?(?:[?#].*)?$"
)


def funda_id_from_url(url: str) -> str:
    match = _DETAIL_URL.match(url.strip())
    if match is None:
        raise InvalidListingUrl(url)
    return match.group(1)
