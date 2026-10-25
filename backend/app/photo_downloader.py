"""Photo downloader adapter: fetches one Listing photo the Listing itself names. Never crawls.

Only https URLs on funda's own hosts are fetched, and only images up to a size cap. The HTTP call
goes through `transport` so tests can replace it; the default uses the standard library.
"""

import urllib.request
from collections.abc import Callable
from urllib.parse import urlparse

TIMEOUT_SECONDS = 30
MAX_PHOTO_BYTES = 15 * 1024 * 1024
ALLOWED_HOST_SUFFIXES = (".funda.nl", ".funda.io")

# (url, byte limit) -> (content type, body read up to limit + 1 bytes)
Transport = Callable[[str, int], tuple[str, bytes]]


class PhotoUnavailable(Exception):
    pass


def _urllib_transport(url: str, limit: int) -> tuple[str, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": "funda-griller/0.1"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        if not _is_funda_photo_url(response.geturl()):
            raise PhotoUnavailable("redirected off funda")
        return response.headers.get_content_type(), response.read(limit)


def _is_funda_photo_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and (parsed.hostname or "").lower().endswith(ALLOWED_HOST_SUFFIXES)


class HttpPhotoDownloader:
    def __init__(self, transport: Transport = _urllib_transport, max_bytes: int = MAX_PHOTO_BYTES) -> None:
        self.transport = transport
        self.max_bytes = max_bytes

    def download(self, url: str) -> bytes:
        if not _is_funda_photo_url(url):
            raise PhotoUnavailable("not a funda photo URL")
        content_type, body = self.transport(url, self.max_bytes + 1)
        if not content_type.startswith("image/"):
            raise PhotoUnavailable("not an image")
        if len(body) > self.max_bytes:
            raise PhotoUnavailable("photo too large")
        return body
