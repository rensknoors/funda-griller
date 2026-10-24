from funda import Funda

from app.ports import Ports
from app.pyfunda_provider import PyfundaListingProvider
from app.settings import Settings
from app.source_clients import (
    EpOnlineEnergielabelSource,
    KlimaateffectatlasFloodSoilSource,
    PyfundaWozSource,
    RivmNoiseSource,
)


def build_production_ports(settings: Settings) -> Ports:
    funda = Funda()
    return Ports(
        listing_provider=PyfundaListingProvider(funda),
        source_clients={
            "energielabel": EpOnlineEnergielabelSource(settings.ep_online_api_key),
            "woz": PyfundaWozSource(funda),
            "flood_soil": KlimaateffectatlasFloodSoilSource(),
            "noise": RivmNoiseSource(),
        },
    )
