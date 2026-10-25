from funda import Funda

from app.document_downloader import HttpDocumentDownloader
from app.gemini_client import GeminiLlmClient
from app.photo_downloader import HttpPhotoDownloader
from app.ports import Ports
from app.pyfunda_provider import PyfundaListingProvider
from app.settings import Settings
from app.source_clients import (
    EpOnlineEnergielabelSource,
    KlimaateffectatlasFloodSoilSource,
    PyfundaComparablesSource,
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
            "comparables": PyfundaComparablesSource(funda, settings.comparables_max_fetches),
        },
        llm_client=GeminiLlmClient(
            settings.gemini_api_key, settings.vision_model, settings.verdict_model
        ),
        photo_downloader=HttpPhotoDownloader(),
        document_downloader=HttpDocumentDownloader(),
    )
