"""Document downloader adapter: fetches the funda brochure PDF the Listing links to.

funda's media host answers 403 without a browser user agent. Only the one URL the Listing names is
fetched; nothing is crawled.
"""

import urllib.request
from collections.abc import Callable

from app.ports import DownloadFailed

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
TIMEOUT_SECONDS = 60
MAX_BYTES = 50 * 1024 * 1024

Get = Callable[[str, dict], bytes]


def _urllib_get(url: str, headers: dict) -> bytes:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        content = response.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise ValueError("Document larger than the download limit")
    return content


class HttpDocumentDownloader:
    def __init__(self, get: Get = _urllib_get) -> None:
        self.get = get

    def download(self, url: str) -> bytes:
        if not url.startswith("https://"):
            raise DownloadFailed("only https URLs are downloaded")
        try:
            return self.get(url, {"User-Agent": BROWSER_USER_AGENT, "Accept": "application/pdf,*/*"})
        except (OSError, ValueError) as error:
            raise DownloadFailed(f"download failed: {type(error).__name__}") from error
