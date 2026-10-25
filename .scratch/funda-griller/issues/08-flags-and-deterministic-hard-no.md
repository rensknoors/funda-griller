# 08: Flags and deterministic Hard no

**What to build:** Declarative, versioned Flag rules produce pros, cons and risks in the Case, each citing its rule and the facts behind it, grouped on the Case detail screen. If the Case hits a deal-breaker from the Buyer Profile, the result is a deterministic Hard no with the reason displayed. Starts with a small set of rules; the structure makes adding more a data change.

**Blocked by:** 06 (Case with affordability)

**Status:** resolved

- [x] Rules are declarative and versioned; a Flag records rule id, rule version and evidence facts
- [x] A starter set covers at least: poor energielabel versus tolerance, ask far above WOZ, ask beyond affordability headroom, and a missing must-have
- [x] Thresholds can depend on derived Buyer Profile values
- [x] Flags appear on the Case detail grouped as pro, con and risk, each expandable to rule and evidence
- [x] A deal-breaker hit sets the tier to Hard no deterministically and displays which deal-breaker caused it
- [x] Changing the profile or the rules produces a new Case version
- [x] API tests cover each starter rule and a deal-breaker forcing Hard no

## Comments

- Rules live in `config/flag_rules.toml` (set `version` plus per-rule `version`); condition kinds in `backend/app/flags.py`. The Case records `built_from.flag_rules_version`, each Flag its `rule_id`, `rule_version` and evidence, and `hard_no` names the deal-breaker and the Flag that hit it.
- Must-haves and deal-breakers are free text: they are checked when they name a feature from the rules file (matched by alias, looked up in the Listing description). A deal-breaker naming a feature is hit when the Listing mentions it; one containing a rule's `deal_breaker_aliases` is hit when that rule raises a Flag. Unrecognised preferences are not checked.
- `ask_far_above_woz` reads `woz_value`, and the energielabel rules prefer `official_energy_label` over the Listing's `energy_label`; both arrive with ticket 07. Its positive API test is skipped until 07 puts WOZ facts in the Case: align the fact keys in `flag_rules.toml` with 07 and un-skip it.
