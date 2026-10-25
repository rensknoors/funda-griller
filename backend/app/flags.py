"""Flag rules: a declarative, versioned rule set evaluated over Case facts. No I/O, no judgement.

A rule reads facts by key and raises a Flag (pro, con or risk) citing its rule id, rule version and
the evidence facts. Adding a rule that uses an existing condition kind, or a feature, is a change to
the rules file only.
"""

import re
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


def _not_one_of(rule: dict, facts: dict[str, dict], _: RuleSet) -> list[Hit]:
    """The fact is present and its value is none of the rule's `values`, ignoring case and spacing
    (e.g. an Eigendomssituatie other than "Volle eigendom")."""
    fact = _first_fact(facts, rule["fact"])
    allowed = {str(value).strip().casefold() for value in rule["values"]}
    if fact is None or str(fact["value"]).strip().casefold() in allowed:
        return []
    return [(None, [fact])]


_WORD = re.compile(r"[\w+]+")
_CLAUSE_BREAK = re.compile(r"[.,;:!?()\n]")
# Words that negate the feature named shortly after them in a Listing description ("geen garage",
# "zonder tuin", "niet op erfpacht").
_NEGATIONS = frozenset({"geen", "géén", "niet", "zonder"})
_NEGATION_REACH = 3


def _words(text: str) -> list[str]:
    return _WORD.findall(text.casefold())


def names(text: str, phrase: str) -> bool:
    """Whether `text` contains `phrase` as whole words: "dak" is not named by "dakterras"."""
    words, wanted = _words(text), _words(phrase)
    return any(words[i : i + len(wanted)] == wanted for i in range(len(words) - len(wanted) + 1))


def _has(description: str, word: str) -> bool:
    """Whether the description says the house has `word`: a whole word, or the head of a Dutch
    compound ("achtertuin" is a tuin, "dakterras" is no dak), and not negated within its clause
    ("geen garage", "zonder tuin")."""
    wanted = word.casefold()
    for clause in _CLAUSE_BREAK.split(description):
        words = _words(clause)
        for i, token in enumerate(words):
            if token == wanted or (token.endswith(wanted) and len(token) - len(wanted) >= 3):
                if not _NEGATIONS.intersection(words[max(0, i - _NEGATION_REACH) : i]):
                    return True
    return False


def _matching_feature(preference: str, rule_set: RuleSet) -> dict | None:
    """The feature a free-text preference names, by alias, or None when none matches. The
    preference's own negation ("Geen erfpacht") does not change which feature it names."""
    return next((f for f in rule_set.features if any(names(preference, a) for a in f["aliases"])), None)


def _feature_evidence(feature: dict, facts: dict[str, dict]) -> dict | None:
    """Whether the Listing says it has the feature, as an evidence item; None without a description."""
    description = facts.get("description")
    if description is None:
        return None
    text = str(description["value"])
    return {
        "key": f"{feature['id']}_mentioned",
        "value": any(_has(text, word) for word in feature["mentioned"]),
        "provenance": description["provenance"],
        "fetched_at": description.get("fetched_at"),
    }


def _preferences(facts: dict[str, dict], key: str) -> list[str]:
    preferences = facts.get(key)
    return list(preferences["value"]) if preferences else []


def _preference(key: str, value: str, facts: dict[str, dict]) -> dict:
    return {**facts[f"{key}s"], "key": key, "value": value}


def _feature_hits(facts: dict[str, dict], rule_set: RuleSet, key: str, when: bool) -> list[Hit]:
    """One hit per `key` preference naming a feature whose presence in the Listing is `when`."""
    hits: list[Hit] = []
    for preference in _preferences(facts, f"{key}s"):
        feature = _matching_feature(preference, rule_set)
        mentioned = feature and _feature_evidence(feature, facts)
        if mentioned and mentioned["value"] is when:
            hits.append((preference, [_preference(key, preference, facts), mentioned]))
    return hits


def _must_have_missing(rule: dict, facts: dict[str, dict], rule_set: RuleSet) -> list[Hit]:
    return _feature_hits(facts, rule_set, "must_have", when=False)


def _deal_breaker_mentioned(rule: dict, facts: dict[str, dict], rule_set: RuleSet) -> list[Hit]:
    """A deal-breaker naming a feature is hit when the Listing has it: "Geen erfpacht" and
    "Erfpacht" both rule out a house on erfpacht."""
    return _feature_hits(facts, rule_set, "deal_breaker", when=True)


_LABEL = re.compile(r"(?<![\w+])([a-g]\+{0,4})(?![\w+])")
_WORSE_THAN = re.compile(r"(slechter dan|onder|lager dan)\s+([a-g]\+{0,4})(?![\w+])")
_OR_WORSE = re.compile(r"(?<![\w+])([a-g]\+{0,4})\s+(of|en)\s+(slechter|lager)")


def _worse_than(label: object, or_equal: bool = False) -> list[str]:
    floor = _label_rank(label)
    if floor is None:
        return []
    return [label for rank, label in enumerate(ENERGY_LABELS) if rank > floor or (or_equal and rank == floor)]


def named_energy_labels(text: str) -> list[str] | None:
    """The energielabels a deal-breaker names, best first: "Energielabel F of G" names F and G,
    "slechter dan C" and "D of slechter" name D to G. Empty when it is about the energielabel but
    names none ("Slecht energielabel"); None when it is not about the energielabel."""
    folded = text.casefold()
    if not (names(folded, "energielabel") or names(folded, "label")):
        return None
    if match := _WORSE_THAN.search(folded):
        return _worse_than(match.group(2))
    if match := _OR_WORSE.search(folded):
        return _worse_than(match.group(1), or_equal=True)
    named = {label.upper() for label in _LABEL.findall(folded)}
    return [label for label in ENERGY_LABELS if label in named]


def _deal_breaker_energy_label(rule: dict, facts: dict[str, dict], _: RuleSet) -> list[Hit]:
    """A deal-breaker naming energielabels is hit when the house's label is one of them. One about
    the energielabel naming none is hit by a label worse than the renovation tolerance allows."""
    fact = _first_fact(facts, rule["fact"])
    hits: list[Hit] = []
    for deal_breaker in _preferences(facts, "deal_breakers") if fact else []:
        labels = named_energy_labels(deal_breaker)
        if labels is None:
            continue
        preference = _preference("deal_breaker", deal_breaker, facts)
        if labels:
            limit = {**preference, "key": "named_energy_labels", "value": labels}
        elif threshold := _threshold(rule, facts):
            labels, limit = _worse_than(threshold["value"]), threshold
        else:
            continue
        if str(fact["value"]).strip().upper() in labels:
            hits.append((deal_breaker, [preference, fact, limit]))
    return hits


_CONDITIONS: dict[str, Condition] = {
    "label_worse_than": _label_worse_than,
    "label_at_least": _label_at_least,
    "below": _below,
    "above": _above,
    "ratio_above": _ratio_above,
    "equals": _equals,
    "not_one_of": _not_one_of,
    "must_have_missing": _must_have_missing,
    "deal_breaker_mentioned": _deal_breaker_mentioned,
    "deal_breaker_energy_label": _deal_breaker_energy_label,
}

# Condition kinds that raise one Flag per Buyer Profile deal-breaker they find hit.
_DEAL_BREAKER_KINDS = frozenset({"deal_breaker_mentioned", "deal_breaker_energy_label"})


def hard_no(rule_set: RuleSet, deal_breakers: list[str], flags: list[dict]) -> dict | None:
    """The first Buyer Profile deal-breaker a raised Flag hits, as a deterministic Hard no.

    A deal-breaker is hit by a Flag raised about it (a feature the Listing has, an energielabel it
    names), or by any Flag from a rule one of whose `deal_breaker_aliases` it names as whole words.
    """
    for deal_breaker in deal_breakers:
        about_it = {
            f"{rule['id']}:{deal_breaker}" for rule in rule_set.rules if rule["kind"] in _DEAL_BREAKER_KINDS
        }
        named_rules = {
            rule["id"]
            for rule in rule_set.rules
            if any(names(deal_breaker, alias) for alias in rule.get("deal_breaker_aliases", ()))
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
