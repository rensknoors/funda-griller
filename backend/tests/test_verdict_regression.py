"""The Verdict regression set, driven through its command with the fake LLM client. Never the real model."""

import io
import json

import pytest

from app.ports import LlmError, SourceFact
from app.verdict_regression import main
from tests.listing_fixtures import LIVE_URL, live_listing
from tests.pdf_fixtures import make_pdf
from tests.profile_fixtures import typical_profile

SNAPSHOT = {
    "address": "Buchterweg 15",
    "city": "Holtum",
    "status": "available",
    "asking_price": 595_000,
    "living_area": 152,
    "construction_year": 1931,
    "energy_label": "B",
    "fetched_at": "2026-10-20T09:00:00+00:00",
}


def entry(expected_tier, **overrides):
    return {
        "expected_tier": expected_tier,
        "as_of": "2026-10-24T12:00:00+00:00",
        "snapshot": SNAPSHOT,
        "source_runs": {},
        "buyer_profile": typical_profile(),
        **overrides,
    }


@pytest.fixture
def regression_set(tmp_path):
    directory = tmp_path / "set"
    directory.mkdir()

    def write(name, content):
        (directory / f"{name}.json").write_text(json.dumps(content))

    write.directory = directory
    return write


def run(settings, llm_client, *argv):
    out = io.StringIO()
    if argv[0] == "run":
        argv = (*argv, "--results", str(settings.database_path.parent / "results"))
    code = main(list(argv), settings=settings, llm_client=llm_client, out=out)
    return code, out.getvalue()


def answer(tier):
    bid = {"opening_bid": 580_000, "walk_away_maximum": 600_000, "conditions": ["Bouwkundige keuring"]}
    return {
        "tier": tier,
        "summary": "Samenvatting.",
        "reasoning": "Onderbouwing.",
        "cited_flags": [],
        "bid_advice": bid if tier in ("must_buy", "consider") else None,
    }


def test_prints_expected_versus_actual_per_listing_and_the_agreement(settings, llm_client, regression_set):
    regression_set("holtum-agrees", entry("consider"))
    regression_set("holtum-disagrees", entry("must_buy"))
    llm_client.verdict = answer("consider")

    code, output = run(settings, llm_client, "run", "--yes", "--set", str(regression_set.directory))

    lines = output.splitlines()
    assert any("holtum-agrees" in line and "consider" in line and "OK" in line for line in lines)
    assert any("holtum-disagrees" in line and "must_buy" in line and "consider" in line and "DIFF" in line for line in lines)
    assert "1/2" in output
    assert code == 1


def test_nothing_runs_without_confirming_the_cost(settings, llm_client, regression_set):
    regression_set("holtum", entry("consider"))

    code, output = run(settings, llm_client, "run", "--set", str(regression_set.directory))

    assert code == 2
    assert "COSTS MONEY" in output
    assert llm_client.rate_calls == []


def test_results_record_the_model_rule_version_and_prompt_version(tmp_path, settings, llm_client, regression_set):
    rules = tmp_path / "flag_rules.toml"
    rules.write_text("version = 7\n")
    settings = settings.model_copy(update={"flag_rules_path": rules, "verdict_model": "gemini-test-model"})
    regression_set("holtum", entry("consider"))
    llm_client.verdict = answer("consider")

    code, output = run(settings, llm_client, "run", "--yes", "--set", str(regression_set.directory))

    assert code == 0
    assert "gemini-test-model" in output
    assert "flag rule set version: 7" in output
    [results_file] = (settings.database_path.parent / "results").glob("*.json")
    record = json.loads(results_file.read_text())
    assert record["model"] == "gemini-test-model"
    assert record["flag_rules_version"] == 7
    assert isinstance(record["prompt_version"], int)
    assert f"prompt version: {record['prompt_version']}" in output
    assert record["results"] == [
        {"name": "holtum", "expected": "consider", "actual": "consider", "outcome": "OK", "error": None, "deterministic": False}
    ]


@pytest.mark.parametrize(
    ("model_answer", "reported"),
    [(answer("maybe"), "invalid_verdict"), (LlmError("quota"), "llm_unavailable")],
)
def test_a_failed_model_answer_is_reported_and_the_rest_still_runs(
    settings, llm_client, regression_set, model_answer, reported
):
    regression_set("a-fails", entry("consider"))
    regression_set("b-runs", entry("skip"))

    def rate(case, _profile):
        if case["funda_id"] != "a-fails":
            return answer("skip")
        if isinstance(model_answer, Exception):
            raise model_answer
        return model_answer

    llm_client.verdict = rate

    code, output = run(settings, llm_client, "run", "--yes", "--set", str(regression_set.directory))

    assert any("ERROR" in line and "a-fails" in line and reported in line for line in output.splitlines())
    assert any("OK" in line and "b-runs" in line for line in output.splitlines())
    assert "1/2" in output
    assert code == 1


def test_a_deal_breaker_hit_is_a_hard_no_without_a_model_call(settings, llm_client, regression_set):
    profile = {**typical_profile(), "renovation_tolerance": 1, "deal_breakers": ["slecht energielabel"]}
    regression_set("label-g", entry("hard_no", snapshot={**SNAPSHOT, "energy_label": "G"}, buyer_profile=profile))

    code, output = run(settings, llm_client, "run", "--yes", "--set", str(regression_set.directory))

    assert code == 0
    assert "deterministic" in output
    assert llm_client.rate_calls == []


def test_a_captured_listing_can_be_added_to_the_set_and_run(
    client, settings, listing_provider, source_clients, llm_client, regression_set
):
    listing_provider.listings[LIVE_URL] = live_listing()
    source_clients["woz"].facts = [SourceFact("woz_value", 480_000, "2026-01-01")]
    client.post("/api/listings", json={"url": LIVE_URL})
    client.put("/api/buyer-profile", json=typical_profile())
    directory = str(regression_set.directory)

    code, output = run(
        settings, llm_client, "add", "80907644", "--expect", "skip", "--name", "holtum-woz", "--set", directory
    )
    assert code == 0
    assert "holtum-woz" in output

    seen = []
    llm_client.verdict = lambda case, _profile: seen.append(case) or answer("skip")
    code, output = run(settings, llm_client, "run", "--yes", "--set", directory)

    assert code == 0
    assert any("OK" in line and "holtum-woz" in line for line in output.splitlines())
    [case] = seen
    assert case["metrics"]["asking_vs_woz"]["woz_value"] == 480_000
    assert case["metrics"]["asking_vs_woz"]["asking_price"] == 595_000


def test_adding_an_unknown_listing_fails(settings, llm_client, regression_set):
    code, output = run(
        settings, llm_client, "add", "999", "--expect", "skip", "--name", "x", "--set", str(regression_set.directory)
    )

    assert code == 1
    assert "999" in output
    assert list(regression_set.directory.iterdir()) == []


def test_the_shipped_set_is_well_formed(settings, llm_client):
    llm_client.verdict = answer("consider")

    code, output = run(settings, llm_client, "run", "--yes")

    assert "ERROR" not in output
    total = int(output.split("Agreement: ")[1].split("/")[1].split()[0])
    assert total >= 3


ERFPACHT_DOCUMENT = {
    "id": 1,
    "kind": "user",
    "name": "Vragenlijst.pdf",
    "sha256": "abc",
    "status": "analysed",
    "reason": None,
    "page_count": 1,
    "findings": [
        {
            "topic": "erfpacht",
            "present": True,
            "statement": "Erfpacht, canon afgekocht.",
            "quote": "erfpacht",
            "page": 1,
            "verified": True,
        }
    ],
    "rejected_findings": 0,
    "added_at": "2026-10-20T09:00:00+00:00",
    "extracted_at": "2026-10-20T09:00:00+00:00",
}


def test_an_entrys_document_findings_count_like_in_the_app(settings, llm_client, regression_set):
    profile = {**typical_profile(), "deal_breakers": ["Geen erfpacht"]}
    regression_set("erfpacht", entry("hard_no", buyer_profile=profile, documents=[ERFPACHT_DOCUMENT]))

    code, output = run(settings, llm_client, "run", "--yes", "--set", str(regression_set.directory))

    assert code == 0, output
    assert llm_client.rate_calls == []


def test_an_entrys_observations_count_like_in_the_app(settings, llm_client, regression_set):
    observed = {
        "id": 1,
        "attempted_at": "2026-10-20T09:00:00+00:00",
        "outcome": "succeeded",
        "reason": None,
        "model": "vision",
        "observations": [{"key": "damp_or_mould", "value": True, "photos": [1], "note": "Schimmel"}],
    }
    snapshot = {**SNAPSHOT, "photos": [{"number": 1, "url": "/api/listings/x/photos/a.jpg"}]}
    regression_set("damp", entry("skip", snapshot=snapshot, observation_run=observed))
    seen = []
    llm_client.verdict = lambda case, _profile: seen.append(case) or answer("skip")

    run(settings, llm_client, "run", "--yes", "--set", str(regression_set.directory))

    [case] = seen
    assert "damp_or_mould_visible" in {flag["rule_id"] for flag in case["flags"]}


def test_adding_a_listing_freezes_its_observations_and_documents(
    client, settings, listing_provider, llm_client, regression_set
):
    llm_client.observations = [{"key": "damp_or_mould", "value": True, "photos": [1]}]
    listing_provider.listings[LIVE_URL] = live_listing(brochure_url=None)
    client.post("/api/listings", json={"url": LIVE_URL})
    client.put("/api/buyer-profile", json=typical_profile() | {"deal_breakers": ["Asbest"]})
    llm_client.findings = [
        {"topic": "asbestos", "present": True, "statement": "Asbest.", "quote": "asbest aanwezig", "page": 1}
    ]
    client.post(
        "/api/listings/80907644/documents",
        files={"file": ("Vragenlijst.pdf", make_pdf(["Er is asbest aanwezig."]), "application/pdf")},
    )
    directory = str(regression_set.directory)
    run(settings, llm_client, "add", "80907644", "--expect", "hard_no", "--name", "holtum", "--set", directory)
    llm_client.findings = []

    code, output = run(settings, llm_client, "run", "--yes", "--set", directory)

    assert code == 0, output
    assert llm_client.rate_calls == []
    frozen = json.loads((regression_set.directory / "holtum.json").read_text())
    assert [o["key"] for o in frozen["observation_run"]["observations"]] == ["damp_or_mould"]
    assert "stored_name" not in frozen["documents"][0]
