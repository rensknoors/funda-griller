"""Listing photos kept on disk with the snapshot, and Observations extracted from them once."""

from pathlib import Path

from app.ports import LlmError
from tests.listing_fixtures import LIVE_URL, live_listing
from tests.profile_fixtures import typical_profile

PHOTO_1 = "https://cloud.funda.nl/p1.jpg"
PHOTO_2 = "https://cloud.funda.nl/p2.jpg"

KITCHEN = {"key": "kitchen_age_years", "value": 25, "photos": [2], "note": "Eikenhouten keuken"}
DAMP = {"key": "damp_or_mould", "value": True, "photos": [1, 2], "note": "Vochtplek boven het raam"}


def capture(client, listing_provider, **overrides):
    listing_provider.listings[LIVE_URL] = live_listing(**overrides)
    response = client.post("/api/listings", json={"url": LIVE_URL})
    assert response.status_code == 201, response.text
    return response.json()


def read_case(client):
    return client.get("/api/listings/80907644/case").json()


def observations(case):
    return {f["key"]: f for f in case["facts"] if f["provenance"] == "observation"}


def test_listing_photos_are_downloaded_with_the_snapshot_and_served_by_the_app(
    client, listing_provider, photo_downloader
):
    photo_downloader.photos = {PHOTO_1: b"voorgevel", PHOTO_2: b"keuken"}

    snapshot = capture(client, listing_provider)["snapshots"][0]

    assert photo_downloader.calls == [PHOTO_1, PHOTO_2]
    assert [photo["source_url"] for photo in snapshot["photos"]] == [PHOTO_1, PHOTO_2]
    assert [photo["number"] for photo in snapshot["photos"]] == [1, 2]
    served = [client.get(photo["url"]) for photo in snapshot["photos"]]
    assert [r.content for r in served] == [b"voorgevel", b"keuken"]
    assert all(p["url"].startswith("/api/listings/80907644/photos/") for p in snapshot["photos"])


def test_a_refetch_keeps_photos_already_on_disk_instead_of_downloading_them_again(
    client, listing_provider, photo_downloader
):
    capture(client, listing_provider)

    refetched = client.post("/api/listings/80907644/refetch").json()

    assert photo_downloader.calls == [PHOTO_1, PHOTO_2]
    first, second = refetched["snapshots"][1], refetched["snapshots"][0]
    assert [p["url"] for p in second["photos"]] == [p["url"] for p in first["photos"]]


def test_a_photo_that_cannot_be_downloaded_is_left_out_without_failing_the_capture(
    client, listing_provider, photo_downloader
):
    photo_downloader.photos = {PHOTO_1: OSError("timed out"), PHOTO_2: b"keuken"}

    snapshot = capture(client, listing_provider)["snapshots"][0]

    assert [(p["number"], p["source_url"]) for p in snapshot["photos"]] == [(1, PHOTO_2)]


def test_observations_are_extracted_at_capture_and_cite_their_photos_as_estimates(
    client, listing_provider, llm_client, photo_downloader
):
    photo_downloader.photos = {PHOTO_1: b"voorgevel", PHOTO_2: b"keuken"}
    llm_client.observations = [KITCHEN]

    capture(client, listing_provider)
    case = read_case(client)

    [paths] = llm_client.observe_calls
    assert [Path(p).read_bytes() for p in paths] == [b"voorgevel", b"keuken"]
    kitchen = observations(case)["kitchen_age_years"]
    assert kitchen["value"] == 25
    assert kitchen["estimated"] is True
    assert kitchen["note"] == "Eikenhouten keuken"
    assert kitchen["extracted_at"] == "2026-10-24T12:00:00+00:00"
    [cited] = kitchen["photos"]
    assert cited["number"] == 2
    assert client.get(cited["url"]).content == b"keuken"
    assert case["observations"]["status"] == "succeeded"
    assert [p["number"] for p in case["photos"]] == [1, 2]


def test_observations_the_vision_model_got_wrong_are_dropped_at_the_boundary(
    client, listing_provider, llm_client
):
    llm_client.observations = [
        KITCHEN,
        {"key": "swimming_pool", "value": True, "photos": [1]},
        {"key": "roof_condition", "value": "excellent", "photos": [1]},
        {"key": "facade_condition", "value": "poor", "photos": [7]},
        {"key": "bathroom_age_years", "value": "old", "photos": [1]},
        "not an observation",
    ]

    capture(client, listing_provider)

    assert list(observations(read_case(client))) == ["kitchen_age_years"]


def test_unchanged_photos_are_not_analysed_again_on_refetch(client, listing_provider, llm_client):
    llm_client.observations = [KITCHEN]
    capture(client, listing_provider)

    client.post("/api/listings/80907644/refetch")

    assert len(llm_client.observe_calls) == 1
    assert "kitchen_age_years" in observations(read_case(client))


def test_changed_photos_are_analysed_again(client, listing_provider, llm_client):
    capture(client, listing_provider)

    capture_again = live_listing(photo_urls=(PHOTO_1, PHOTO_2, "https://cloud.funda.nl/p3.jpg"))
    listing_provider.listings[LIVE_URL] = capture_again
    client.post("/api/listings/80907644/refetch")

    assert [len(paths) for paths in llm_client.observe_calls] == [2, 3]


def test_analysis_can_be_rerun_on_demand(client, listing_provider, llm_client, clock):
    llm_client.observations = [KITCHEN]
    capture(client, listing_provider)
    clock.advance(days=3)
    llm_client.observations = [{**KITCHEN, "value": 30}]

    response = client.post("/api/listings/80907644/observations")

    assert response.status_code == 200, response.text
    kitchen = observations(response.json())["kitchen_age_years"]
    assert kitchen["value"] == 30
    assert kitchen["extracted_at"] == "2026-10-27T12:00:00+00:00"
    assert len(llm_client.observe_calls) == 2


def test_a_failed_analysis_never_fails_the_capture(client, listing_provider, llm_client):
    llm_client.observations = LlmError("quota")

    capture(client, listing_provider)
    case = read_case(client)

    assert observations(case) == {}
    assert case["observations"]["status"] == "failed"


def test_a_failed_rerun_keeps_the_earlier_observations(client, listing_provider, llm_client):
    llm_client.observations = [KITCHEN]
    capture(client, listing_provider)
    llm_client.observations = LlmError("quota")

    response = client.post("/api/listings/80907644/observations")

    assert response.status_code == 502
    assert response.json()["code"] == "llm_unavailable"
    case = read_case(client)
    assert observations(case)["kitchen_age_years"]["value"] == 25
    assert case["observations"]["status"] == "failed"


def test_a_listing_without_photos_still_builds_a_full_case(client, listing_provider, llm_client):
    capture(client, listing_provider, photo_urls=())

    case = read_case(client)

    assert llm_client.observe_calls == []
    assert case["photos"] == []
    assert case["observations"]["status"] == "no_photos"
    assert any(f["key"] == "asking_price" for f in case["facts"])


def test_uploaded_photos_of_a_manual_entry_are_analysed(client, llm_client):
    llm_client.observations = [KITCHEN]
    files = [
        ("photos", ("voorgevel.jpg", b"voorgevel", "image/jpeg")),
        ("photos", ("keuken.jpg", b"keuken", "image/jpeg")),
    ]

    client.post("/api/listings/manual", data={"url": LIVE_URL, "raw_status": "Beschikbaar"}, files=files)

    [paths] = llm_client.observe_calls
    assert [Path(p).read_bytes() for p in paths] == [b"voorgevel", b"keuken"]
    assert "kitchen_age_years" in observations(read_case(client))


def test_an_observation_raises_a_flag_citing_it_as_evidence(client, listing_provider, llm_client):
    llm_client.observations = [DAMP]
    capture(client, listing_provider)

    flag = next(f for f in read_case(client)["flags"] if f["rule_id"] == "damp_or_mould_visible")

    assert flag["class"] == "risk"
    [evidence] = flag["evidence"]
    assert evidence["provenance"] == "observation"
    assert evidence["estimated"] is True
    assert [p["number"] for p in evidence["photos"]] == [1, 2]


def test_an_observation_can_hit_a_deal_breaker(client, listing_provider, llm_client):
    llm_client.observations = [DAMP]
    capture(client, listing_provider)
    client.put("/api/buyer-profile", json=typical_profile() | {"deal_breakers": ["Vocht of schimmel"]})

    hard_no = read_case(client)["hard_no"]

    assert hard_no["deal_breaker"] == "Vocht of schimmel"
    assert hard_no["flag_id"] == "damp_or_mould_visible"


def test_rerunning_the_analysis_makes_the_verdict_out_of_date(client, listing_provider, llm_client):
    llm_client.observations = [KITCHEN]
    capture(client, listing_provider)
    client.put("/api/buyer-profile", json=typical_profile())
    client.post("/api/listings/80907644/verdict")
    [(case_sent, _)] = llm_client.rate_calls
    assert any(f["provenance"] == "observation" for f in case_sent["facts"])

    client.post("/api/listings/80907644/observations")

    state = client.get("/api/listings/80907644/verdict").json()
    assert state["out_of_date"] is True
    assert state["changed"] == ["case"]
