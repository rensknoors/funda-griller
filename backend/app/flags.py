"""Flag rules: a declarative, versioned rule set evaluated over Case facts. No I/O, no judgement.

A rule reads facts by key and raises a Flag (pro, con or risk) citing its rule id, rule version and
the evidence facts. Adding a rule that uses an existing condition kind, or a feature, is a change to
the rules file only.
"""

from collections.abc import Callable
from dataclasses import dataclass

ENERGY_LABELS = ("A++++", "A+++", "A++", "A+", "A", "B", "C", "D", "E", "F", "G")


@dataclass(frozen=True)
class RuleSet:
    version: int
    rules: tuple[dict, ...]
    features: tuple[dict, ...]


# A hit is (subject, evidence): subject names what the Flag is about when one rule can raise
# several Flags (one per must-have), else None.
Hit = tuple[str | None, list[dict]]
Condition = Callable[[dict, dict[str, dict], RuleSet], list[Hit]]


def _label_rank(label: object) -> int | None:
    normalised = str(label).strip().upper()
    return ENERGY_LABELS.index(normalised) if normalised in ENERGY_LABELS else None


def _first_fact(facts: dict[str, dict], keys: str | list[str]) -> dict | None:
    for key in [keys] if isinstance(keys, str) else keys:
        if facts.get(key) is not None:
            return facts[key]
    return None


def _threshold(rule: dict, facts: dict[str, dict]) -> dict | None:
    """The threshold as an evidence item, or None when the profile value it depends on is absent."""
    threshold = rule["threshold"]
    if not isinstance(threshold, dict):
        return {"key": "threshold", "value": threshold, "provenance": "rule"}
    depends_on = facts.get(threshold["from_profile"])
    if depends_on is None:
        return None
    value = threshold["table"].get(str(depends_on["value"]))
    if value is None:
        return None
    return {"key": threshold["name"], "value": value, "provenance": "buyer_profile"}


def _label_worse_than(rule: dict, facts: dict[str, dict], _: RuleSet) -> list[Hit]:
    fact, threshold = _first_fact(facts, rule["fact"]), _threshold(rule, facts)
    if fact is None or threshold is None:
        return []
    rank, limit = _label_rank(fact["value"]), _label_rank(threshold["value"])
    if rank is None or limit is None or rank <= limit:
        return []
    return [(None, [fact, threshold])]


def _label_at_least(rule: dict, facts: dict[str, dict], _: RuleSet) -> list[Hit]:
    fact, threshold = _first_fact(facts, rule["fact"]), _threshold(rule, facts)
    if fact is None or threshold is None:
        return []
    rank, limit = _label_rank(fact["value"]), _label_rank(threshold["value"])
    if rank is None or limit is None or rank > limit:
        return []
    return [(None, [fact, threshold])]


def _below(rule: dict, facts: dict[str, dict], _: RuleSet) -> list[Hit]:
    fact, threshold = _first_fact(facts, rule["fact"]), _threshold(rule, facts)
    if fact is None or threshold is None or not fact["value"] < threshold["value"]:
        return []
    return [(None, [fact, threshold])]


def _above(rule: dict, facts: dict[str, dict], _: RuleSet) -> list[Hit]:
    fact, threshold = _first_fact(facts, rule["fact"]), _threshold(rule, facts)
    if fact is None or threshold is None or not fact["value"] > threshold["value"]:
        return []
    return [(None, [fact, threshold])]


def _ratio_above(rule: dict, facts: dict[str, dict], _: RuleSet) -> list[Hit]:
    fact, of = _first_fact(facts, rule["fact"]), _first_fact(facts, rule["of"])
    threshold = _threshold(rule, facts)
    if fact is None or of is None or threshold is None or not of["value"]:
        return []
    ratio = round(fact["value"] / of["value"], 2)
    if ratio <= threshold["value"]:
        return []
    ratio_fact = {"key": rule["ratio_name"], "value": ratio, "provenance": "computed"}
    return [(None, [fact, of, ratio_fact, threshold])]


def _equals(rule: dict, facts: dict[str, dict], _: RuleSet) -> list[Hit]:
    """The fact's value is one of the rule's `values` (e.g. an Observation's `poor` or `true`)."""
    fact = _first_fact(facts, rule["fact"])
    if fact is None or fact["value"] not in rule["values"]:
        return []
    return [(None, [fact])]


def matching_feature(preference: str, rule_set: RuleSet) -> dict | None:
    """The feature a free-text preference names, by alias, or None when none matches."""
    text = preference.casefold()
    return next(
        (f for f in rule_set.features if any(a.casefold() in text for a in f["aliases"])), None
    )


def feature_evidence(feature: dict, facts: dict[str, dict]) -> dict | None:
    """Whether the Listing mentions the feature, as an evidence item; None without a description."""
    description = facts.get("description")
    if description is None:
        return None
    text = str(description["value"]).casefold()
    return {
        "key": f"{feature['id']}_mentioned",
        "value": any(word.casefold() in text for word in feature["mentioned"]),
        "provenance": description["provenance"],
        "fetched_at": description.get("fetched_at"),
    }


def _must_have_missing(rule: dict, facts: dict[str, dict], rule_set: RuleSet) -> list[Hit]:
    must_haves = facts.get("must_haves")
    hits: list[Hit] = []
    for must_have in must_haves["value"] if must_haves else []:
        feature = matching_feature(must_have, rule_set)
        mentioned = feature and feature_evidence(feature, facts)
        if mentioned and not mentioned["value"]:
            preference = {"key": "must_have", "value": must_have, "provenance": "buyer_profile"}
            hits.append((must_have, [preference, mentioned]))
    return hits


def _deal_breaker_mentioned(rule: dict, facts: dict[str, dict], rule_set: RuleSet) -> list[Hit]:
    deal_breakers = facts.get("deal_breakers")
    hits: list[Hit] = []
    for deal_breaker in deal_breakers["value"] if deal_breakers else []:
        feature = matching_feature(deal_breaker, rule_set)
        mentioned = feature and feature_evidence(feature, facts)
        if mentioned and mentioned["value"]:
            preference = {"key": "deal_breaker", "value": deal_breaker, "provenance": "buyer_profile"}
            hits.append((deal_breaker, [preference, mentioned]))
    return hits


_CONDITIONS: dict[str, Condition] = {
    "label_worse_than": _label_worse_than,
    "label_at_least": _label_at_least,
    "below": _below,
    "above": _above,
    "ratio_above": _ratio_above,
    "equals": _equals,
    "must_have_missing": _must_have_missing,
    "deal_breaker_mentioned": _deal_breaker_mentioned,
}


def hard_no(rule_set: RuleSet, deal_breakers: list[str], flags: list[dict]) -> dict | None:
    """The first Buyer Profile deal-breaker a raised Flag hits, as a deterministic Hard no.

    A deal-breaker is hit by the Flag raised about it (a feature the Listing mentions), or by any
    Flag from a rule whose `deal_breaker_aliases` the deal-breaker's text contains.
    """
    for deal_breaker in deal_breakers:
        text = deal_breaker.casefold()
        about_it = {
            f"{rule['id']}:{deal_breaker}"
            for rule in rule_set.rules
            if rule["kind"] == "deal_breaker_mentioned"
        }
        named_rules = {
            rule["id"]
            for rule in rule_set.rules
            if any(alias.casefold() in text for alias in rule.get("deal_breaker_aliases", ()))
        }
        for flag in flags:
            if flag["id"] in about_it or flag["rule_id"] in named_rules:
                return {"tier": "hard_no", "deal_breaker": deal_breaker, "flag_id": flag["id"]}
    return None


def evaluate(rule_set: RuleSet, facts: dict[str, dict]) -> list[dict]:
    """Flags raised by every rule whose condition holds, in rule-file order."""
    flags = []
    for rule in rule_set.rules:
        for subject, evidence in _CONDITIONS[rule["kind"]](rule, facts, rule_set):
            cited = [facts[key] for key in rule.get("cite", ()) if key in facts]
            flags.append(
                {
                    "id": f"{rule['id']}:{subject}" if subject else rule["id"],
                    "rule_id": rule["id"],
                    "rule_version": rule["version"],
                    "class": rule["class"],
                    "title": f"{rule['title']}: {subject}" if subject else rule["title"],
                    "evidence": evidence + cited,
                }
            )
    return flags
