"""Load policy from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from custody.enums import OperationKind
from custody.policy.schema import Policy, PolicyRule, StandingRequirement


def _parse_rule(raw: dict[str, Any]) -> PolicyRule:
    require = raw.get("require", {})
    standing_raw = require.get("standing", {})
    claims = {k: v for k, v in standing_raw.items() if k not in ("ttl_seconds",)}
    ttl = require.get("ttl_seconds", standing_raw.get("ttl_seconds", 900))

    return PolicyRule(
        id=raw["id"],
        ref=raw["ref"],
        allow_ops=frozenset(OperationKind(op) for op in raw.get("allow_ops", [])),
        require_standing=StandingRequirement(claims=claims, ttl_seconds=ttl),
        governor=raw.get("governor", False),
    )


def load_policy(path: Path) -> Policy:
    """Load policy rules from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)

    policy = Policy()
    for raw_rule in data.get("rules", []):
        policy.rules.append(_parse_rule(raw_rule))
    return policy
