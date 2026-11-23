"""The Note (Notitie): the household's own free text per house, outside the Case, which the Verdict
model reads and weighs (ADR-0006)."""

import pytest

from tests.listing_fixtures import LIVE_URL, live_listing
from tests.profile_fixtures import typical_profile

pytestmark = pytest.mark.usefixtures("price_at_asking")

NOTE = "/api/listings/80907644/note"
VERDICT = "/api/listings/80907644/verdict"
NEIGHBOUR = "De buren zeggen dat de fundering van de hele rij is verzakt; bij hen kostte herstel € 80.000."


def capture(client, listing_provider):
    listing_provider.listings[LIVE_URL] = live_listing()
    client.post("/api/listings", json={"url": LIVE_URL})
    client.put("/api/buyer-profile", json=typical_profile())


def test_a_house_has_no_note_until_one_is_written(client, listing_provider):
    capture(client, listing_provider)

    assert client.get(NOTE).json() == {"text": "", "updated_at": None}


def test_a_note_is_kept_per_house_with_the_time_it_changed(client, listing_provider, clock):
    capture(client, listing_provider)

    saved = client.put(NOTE, json={"text": f"  {NEIGHBOUR}\n"})

    assert saved.status_code == 200
    assert saved.json() == {"text": NEIGHBOUR, "updated_at": clock().isoformat()}
    assert client.get(NOTE).json() == saved.json()


def test_an_empty_note_clears_it(client, listing_provider):
    capture(client, listing_provider)
    client.put(NOTE, json={"text": NEIGHBOUR})

    cleared = client.put(NOTE, json={"text": "   "})

    assert cleared.json() == {"text": "", "updated_at": None}
    assert client.get(NOTE).json() == {"text": "", "updated_at": None}


def test_the_verdict_model_reads_the_note_beside_the_case_not_in_it(client, listing_provider, llm_client):
    capture(client, listing_provider)
    case_before = client.get("/api/listings/80907644/case").json()
    client.put(NOTE, json={"text": NEIGHBOUR})

    client.post(VERDICT)

    [(sent_case, _)] = llm_client.rate_calls
    assert llm_client.rate_notes == [NEIGHBOUR]
    assert NEIGHBOUR not in str(sent_case)
    # The Note is not part of the Case: no fact, no Flag, no Hard no follows from it.
    assert client.get("/api/listings/80907644/case").json() == case_before


def test_without_a_note_the_model_reads_none(client, listing_provider, llm_client):
    capture(client, listing_provider)

    client.post(VERDICT)

    assert llm_client.rate_notes == [None]


def test_a_verdict_records_which_note_it_read(client, listing_provider, clock):
    capture(client, listing_provider)
    client.put(NOTE, json={"text": NEIGHBOUR})

    verdict = client.post(VERDICT).json()

    assert verdict["built_from"]["note_updated_at"] == clock().isoformat()
    assert client.get(VERDICT).json()["out_of_date"] is False


def test_changing_the_note_makes_the_verdict_out_of_date(client, listing_provider, clock):
    capture(client, listing_provider)
    client.post(VERDICT)

    clock.advance(1)
    client.put(NOTE, json={"text": NEIGHBOUR})

    state = client.get(VERDICT).json()
    assert state["out_of_date"] is True
    assert state["changed"] == ["note"]
    assert client.get("/api/verdicts/out-of-date").json()["verdicts"][0]["changed"] == ["note"]


def test_clearing_the_note_makes_the_verdict_out_of_date(client, listing_provider, clock):
    capture(client, listing_provider)
    client.put(NOTE, json={"text": NEIGHBOUR})
    client.post(VERDICT)

    clock.advance(1)
    client.put(NOTE, json={"text": ""})

    assert client.get(VERDICT).json()["changed"] == ["note"]


def test_a_note_does_not_soften_a_deal_breaker(client, listing_provider, llm_client):
    listing_provider.listings[LIVE_URL] = live_listing(description="Appartement op erfpacht.")
    client.post("/api/listings", json={"url": LIVE_URL})
    client.put("/api/buyer-profile", json=typical_profile() | {"deal_breakers": ["Geen erfpacht"]})
    client.put(NOTE, json={"text": "De makelaar zegt dat de erfpacht eeuwigdurend is afgekocht."})

    verdict = client.post(VERDICT).json()

    assert verdict["tier"] == "hard_no"
    assert llm_client.rate_calls == []


def test_a_note_needs_a_captured_house(client):
    assert client.put(NOTE, json={"text": NEIGHBOUR}).status_code == 404
    assert client.get(NOTE).status_code == 404
