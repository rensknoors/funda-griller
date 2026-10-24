from funda import Funda

from app.ports import Ports
from app.pyfunda_provider import PyfundaListingProvider
from app.settings import Settings


def build_production_ports(settings: Settings) -> Ports:
    return Ports(listing_provider=PyfundaListingProvider(Funda()))
