from app.ports import Ports
from app.settings import Settings


class _NotBuilt:
    """Placeholder until the real adapter ticket lands."""

    def __init__(self, port: str) -> None:
        self._port = port

    def fetch(self, *_args, **_kwargs):
        raise NotImplementedError(f"{self._port} adapter not built yet")


def build_production_ports(settings: Settings) -> Ports:
    return Ports(listing_provider=_NotBuilt("Listing provider"))
