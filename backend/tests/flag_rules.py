"""The shipped Flag rule set's version, so tests about what a Case records follow rule edits."""

import tomllib

from app.settings import CONFIG_DIR

FLAG_RULES_VERSION = tomllib.loads((CONFIG_DIR / "flag_rules.toml").read_text())["version"]
