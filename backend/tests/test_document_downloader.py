"""The production document downloader, driven through a fake HTTP getter: no network."""

import urllib.error

import pytest

from app.document_downloader import HttpDocumentDownloader
from app.ports import DownloadFailed

URL = "https://cloud.funda.nl/valentina_media/brochure.pdf"


class FakeGet:
    def __init__(self, reply: bytes | Exception) -> None:
        self.reply = reply
        self.requests: list[tuple[str, dict]] = []

    def __call__(self, url: str, headers: dict) -> bytes:
        self.requests.append((url, headers))
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def test_the_brochure_is_fetched_with_a_browser_user_agent():
    get = FakeGet(b"%PDF-1.4 brochure")

    content = HttpDocumentDownloader(get).download(URL)

    assert content == b"%PDF-1.4 brochure"
    [(url, headers)] = get.requests
    assert url == URL
    assert headers["User-Agent"].startswith("Mozilla/5.0")


def test_a_refused_download_is_a_download_failure():
    get = FakeGet(urllib.error.HTTPError(URL, 403, "Forbidden", {}, None))

    with pytest.raises(DownloadFailed):
        HttpDocumentDownloader(get).download(URL)


def test_only_https_urls_are_fetched():
    get = FakeGet(b"%PDF")

    with pytest.raises(DownloadFailed):
        HttpDocumentDownloader(get).download("file:///etc/passwd")
    assert get.requests == []
