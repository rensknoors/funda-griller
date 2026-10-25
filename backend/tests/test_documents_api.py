"""Documents and Findings through the HTTP API, with the fake LLM client and document downloader."""

from app.ports import DownloadFailed, LlmError
from tests.listing_fixtures import LIVE_URL, live_listing
from tests.pdf_fixtures import BROCHURE_PAGES, VRAGENLIJST, make_pdf, real_brochure
from tests.profile_fixtures import typical_profile

ASBESTOS = {
    "topic": "asbestos",
    "present": True,
    "statement": "Asbest in de dakplaten van de schuur.",
    "page": 2,
}


def capture(client, listing_provider, **overrides):
    listing_provider.listings[LIVE_URL] = live_listing(**{"brochure_url": None, **overrides})
    client.post("/api/listings", json={"url": LIVE_URL})


def upload(client, content=VRAGENLIJST, name="Vragenlijst.pdf"):
    return client.post(
        "/api/listings/80907644/documents",
        files={"file": (name, content, "application/pdf")},
    )


def findings_in(case):
    return [fact for fact in case["facts"] if fact["provenance"] == "finding"]


def test_an_uploaded_document_is_listed_and_its_findings_enter_the_case(client, listing_provider, llm_client):
    capture(client, listing_provider)
    llm_client.findings = [ASBESTOS]

    response = upload(client)

    assert response.status_code == 201
    document = response.json()
    assert document["name"] == "Vragenlijst.pdf"
    assert document["kind"] == "upload"
    assert document["status"] == "analysed"
    assert document["page_count"] == 3
    [listed] = client.get("/api/listings/80907644/documents").json()
    assert listed["id"] == document["id"]
    [finding] = findings_in(client.get("/api/listings/80907644/case").json())
    assert finding["key"] == "asbestos"
    assert finding["value"] is True
    assert finding["statement"] == "Asbest in de dakplaten van de schuur."
    assert finding["page"] == 2
    assert finding["document_id"] == document["id"]
    assert finding["document_name"] == "Vragenlijst.pdf"
    assert finding["seller_stated"] is True
    assert finding["extracted_at"] == "2026-10-24T12:00:00+00:00"


def flags_by_rule(case):
    return {flag["rule_id"]: flag for flag in case["flags"]}


def test_a_seller_stated_asbestos_finding_raises_a_risk_flag_citing_its_page(client, listing_provider, llm_client):
    capture(client, listing_provider)
    llm_client.findings = [ASBESTOS]

    upload(client)

    flag = flags_by_rule(client.get("/api/listings/80907644/case").json())["finding_asbestos"]
    assert flag["class"] == "risk"
    assert flag["rule_version"] == 1
    [evidence] = flag["evidence"]
    assert evidence["provenance"] == "finding"
    assert evidence["page"] == 2
    assert evidence["document_name"] == "Vragenlijst.pdf"


def test_a_finding_the_seller_denies_raises_no_flag(client, listing_provider, llm_client):
    capture(client, listing_provider)
    llm_client.findings = [{"topic": "leak", "present": False, "statement": "Geen lekkages.", "page": 3}]

    upload(client)

    case = client.get("/api/listings/80907644/case").json()
    assert "finding_leak" not in flags_by_rule(case)
    assert [f["key"] for f in findings_in(case)] == ["leak"]


def test_removing_a_document_rebuilds_the_case_without_its_findings(client, listing_provider, llm_client):
    capture(client, listing_provider)
    llm_client.findings = [ASBESTOS]
    document = upload(client).json()

    response = client.delete(f"/api/listings/80907644/documents/{document['id']}")

    assert response.status_code == 204
    case = client.get("/api/listings/80907644/case").json()
    assert findings_in(case) == []
    assert "finding_asbestos" not in flags_by_rule(case)
    assert case["documents"] == []
    assert client.get(f"/api/listings/80907644/documents/{document['id']}/file").status_code == 404


def test_re_uploading_a_document_replaces_its_findings(client, listing_provider, llm_client):
    capture(client, listing_provider)
    llm_client.findings = [ASBESTOS]
    document = upload(client).json()
    llm_client.findings = [{"topic": "leak", "present": True, "statement": "Lekkage dakkapel 2023.", "page": 1}]

    response = client.put(
        f"/api/listings/80907644/documents/{document['id']}",
        files={"file": ("Vragenlijst v2.pdf", make_pdf(["Lekkage dakkapel 2023."]), "application/pdf")},
    )

    assert response.json()["name"] == "Vragenlijst v2.pdf"
    assert response.json()["page_count"] == 1
    case = client.get("/api/listings/80907644/case").json()
    assert [(f["key"], f["page"]) for f in findings_in(case)] == [("leak", 1)]
    assert set(flags_by_rule(case)) >= {"finding_leak"}
    assert "finding_asbestos" not in flags_by_rule(case)


def test_a_new_document_makes_the_latest_verdict_out_of_date(client, listing_provider, llm_client):
    capture(client, listing_provider)
    client.put("/api/buyer-profile", json=typical_profile())
    client.post("/api/listings/80907644/verdict")

    upload(client)

    state = client.get("/api/listings/80907644/verdict").json()
    assert state["out_of_date"] is True
    assert state["changed"] == ["case"]


def test_an_unreadable_document_is_reported_and_never_analysed(client, listing_provider, llm_client):
    capture(client, listing_provider)

    document = upload(client, b"PK\x03\x04 a Word file, not a PDF", "Lijst van zaken.docx").json()

    assert document["status"] == "unreadable"
    assert document["reason"] == "not_a_pdf"
    assert llm_client.extract_calls == []
    [summary] = client.get("/api/listings/80907644/case").json()["documents"]
    assert (summary["status"], summary["finding_count"]) == ("unreadable", 0)


def test_a_broken_pdf_is_unreadable(client, listing_provider, llm_client):
    capture(client, listing_provider)

    document = upload(client, VRAGENLIJST[:200]).json()

    assert (document["status"], document["reason"]) == ("unreadable", "corrupt")
    assert llm_client.extract_calls == []


def test_a_failed_extraction_is_reported_and_can_be_retried(client, listing_provider, llm_client):
    capture(client, listing_provider)
    llm_client.findings = LlmError("quota")

    document = upload(client).json()

    assert (document["status"], document["reason"]) == ("not_analysed", "llm_failed")
    assert findings_in(client.get("/api/listings/80907644/case").json()) == []
    llm_client.findings = [ASBESTOS]
    retried = client.post(f"/api/listings/80907644/documents/{document['id']}/analyse").json()
    assert retried["status"] == "analysed"
    assert len(findings_in(client.get("/api/listings/80907644/case").json())) == 1


def test_findings_citing_a_page_the_document_lacks_are_rejected(client, listing_provider, llm_client):
    capture(client, listing_provider)
    llm_client.findings = [
        ASBESTOS,
        ASBESTOS | {"page": 9},
        ASBESTOS | {"topic": "swimming_pool"},
        {"topic": "leak", "present": "maybe", "statement": "?", "page": 1},
    ]

    document = upload(client).json()

    assert document["rejected_findings"] == 3
    assert [f["page"] for f in findings_in(client.get("/api/listings/80907644/case").json())] == [2]


def test_findings_are_extracted_once_per_document_content(client, listing_provider, llm_client):
    capture(client, listing_provider)
    llm_client.findings = [ASBESTOS]
    first = upload(client).json()

    second = upload(client, name="Vragenlijst kopie.pdf").json()
    client.get("/api/listings/80907644/case")

    assert len(llm_client.extract_calls) == 1
    assert second["status"] == "analysed"
    assert second["extracted_at"] == first["extracted_at"]
    assert len(findings_in(client.get("/api/listings/80907644/case").json())) == 2


def test_a_document_is_served_inline_for_the_apps_own_ui_only(client, listing_provider):
    capture(client, listing_provider)
    document = upload(client).json()

    response = client.get(f"/api/listings/80907644/documents/{document['id']}/file")

    assert response.status_code == 200
    assert response.content == VRAGENLIJST
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("inline")
    assert "no-store" in response.headers["cache-control"]


def test_documents_of_an_unknown_listing_are_not_found(client):
    assert client.get("/api/listings/1/documents").status_code == 404
    assert upload(client).status_code == 404


BROCHURE_URL = "https://cloud.funda.nl/brochure.pdf"


def test_the_funda_brochure_is_downloaded_and_attached_as_a_document(
    client, listing_provider, llm_client, document_downloader
):
    document_downloader.documents[BROCHURE_URL] = real_brochure()
    llm_client.findings = [
        {"topic": "stays_or_goes", "present": True, "statement": "Zonnepanelen blijven achter.", "page": 6},
        {"topic": "other", "present": True, "statement": "Bestaat niet.", "page": 33},
    ]

    capture(client, listing_provider, brochure_url=BROCHURE_URL)

    assert document_downloader.calls == [BROCHURE_URL]
    [brochure] = client.get("/api/listings/80907644/documents").json()
    assert brochure["kind"] == "brochure"
    assert brochure["source_url"] == BROCHURE_URL
    assert (brochure["status"], brochure["page_count"]) == ("analysed", BROCHURE_PAGES)
    assert brochure["rejected_findings"] == 1
    [finding] = findings_in(client.get("/api/listings/80907644/case").json())
    assert (finding["key"], finding["page"], finding["document_id"]) == ("stays_or_goes", 6, brochure["id"])


def test_refetching_a_listing_does_not_download_the_same_brochure_again(
    client, listing_provider, llm_client, document_downloader
):
    capture(client, listing_provider, brochure_url=BROCHURE_URL)

    client.post("/api/listings/80907644/refetch")

    assert document_downloader.calls == [BROCHURE_URL]
    assert len(llm_client.extract_calls) == 1
    assert len(client.get("/api/listings/80907644/documents").json()) == 1


def test_a_new_brochure_url_replaces_the_old_brochure(client, listing_provider, document_downloader):
    capture(client, listing_provider, brochure_url=BROCHURE_URL)
    new_url = "https://cloud.funda.nl/brochure-v2.pdf"
    listing_provider.listings[LIVE_URL] = live_listing(brochure_url=new_url)

    client.post("/api/listings/80907644/refetch")

    [brochure] = client.get("/api/listings/80907644/documents").json()
    assert brochure["source_url"] == new_url


def test_a_failed_brochure_download_is_reported_and_can_be_retried(
    client, listing_provider, document_downloader
):
    document_downloader.documents[BROCHURE_URL] = DownloadFailed("403")

    capture(client, listing_provider, brochure_url=BROCHURE_URL)

    [brochure] = client.get("/api/listings/80907644/documents").json()
    assert brochure["status"] == "download_failed"
    del document_downloader.documents[BROCHURE_URL]
    retried = client.post(f"/api/listings/80907644/documents/{brochure['id']}/analyse").json()
    assert (retried["status"], retried["page_count"]) == ("analysed", 2)


def test_a_listing_without_a_brochure_has_no_documents(client, listing_provider, document_downloader):
    capture(client, listing_provider)

    assert client.get("/api/listings/80907644/documents").json() == []
    assert document_downloader.calls == []


def test_erfpacht_in_a_document_forces_a_hard_no_for_an_erfpacht_deal_breaker(client, listing_provider, llm_client):
    capture(client, listing_provider)
    client.put("/api/buyer-profile", json=typical_profile() | {"deal_breakers": ["Geen erfpacht"]})
    llm_client.findings = [
        {"topic": "erfpacht", "present": True, "statement": "Eeuwigdurende erfpacht, canon afgekocht.", "page": 1}
    ]

    upload(client)

    case = client.get("/api/listings/80907644/case").json()
    assert case["hard_no"]["deal_breaker"] == "Geen erfpacht"
    assert case["hard_no"]["flag_id"] == "finding_erfpacht"
    assert client.post("/api/listings/80907644/verdict").json()["tier"] == "hard_no"
    assert llm_client.rate_calls == []
