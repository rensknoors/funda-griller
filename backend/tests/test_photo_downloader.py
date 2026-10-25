"""The HTTP photo downloader, driven through a fake transport: no network."""

import pytest

from app.photo_downloader import HttpPhotoDownloader, PhotoUnavailable


def downloader_with(content_type: str, body: bytes, max_bytes: int = 1_000):
    requested: list[str] = []

    def transport(url: str, limit: int) -> tuple[str, bytes]:
        requested.append(url)
        return content_type, body[:limit]

    return HttpPhotoDownloader(transport, max_bytes=max_bytes), requested


def test_a_funda_photo_is_downloaded():
    downloader, requested = downloader_with("image/jpeg", b"jpeg")

    assert downloader.download("https://cloud.funda.nl/valentina_media/1/2/3.jpg") == b"jpeg"
    assert requested == ["https://cloud.funda.nl/valentina_media/1/2/3.jpg"]


@pytest.mark.parametrize(
    "url",
    ["http://cloud.funda.nl/p.jpg", "https://example.com/p.jpg", "https://funda.nl.evil.com/p.jpg", "file:///etc/passwd"],
)
def test_only_photos_hosted_by_funda_over_https_are_fetched(url):
    downloader, requested = downloader_with("image/jpeg", b"jpeg")

    with pytest.raises(PhotoUnavailable):
        downloader.download(url)
    assert requested == []


def test_a_reply_that_is_not_an_image_is_refused():
    downloader, _ = downloader_with("text/html", b"<html>")

    with pytest.raises(PhotoUnavailable):
        downloader.download("https://cloud.funda.nl/p.jpg")


def test_an_oversized_photo_is_refused():
    downloader, _ = downloader_with("image/jpeg", b"x" * 20, max_bytes=10)

    with pytest.raises(PhotoUnavailable):
        downloader.download("https://cloud.funda.nl/p.jpg")
