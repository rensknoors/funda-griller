"""The shipped Flag rule set's and cost table's versions, so tests about what a Case records follow
edits to them."""

import tomllib

from app.settings import CONFIG_DIR

FLAG_RULES_VERSION = tomllib.loads((CONFIG_DIR / "flag_rules.toml").read_text())["version"]
COST_TABLE_VERSION = tomllib.loads((CONFIG_DIR / "renovation_costs.toml").read_text())["version"]
