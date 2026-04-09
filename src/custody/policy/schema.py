"""Policy rule schema."""

from __future__ import annotations

from dataclasses import dataclass, field

from custody.enums import OperationKind


@dataclass(frozen=True)
class StandingRequirement:
    """Required standing claims for a policy rule."""

    claims: dict[str, str] = field(default_factory=dict)
    ttl_seconds: int = 900


@dataclass(frozen=True)
class PolicyRule:
    """A single policy rule binding a ref to allowed operations and requirements."""

    id: str
    ref: str
    allow_ops: frozenset[OperationKind]
    require_standing: StandingRequirement
    governor: bool = False


@dataclass
class Policy:
    """Collection of policy rules."""

    rules: list[PolicyRule] = field(default_factory=list)

    def match(self, ref_id: str, op: OperationKind) -> PolicyRule | None:
        """Find the first matching rule for a ref and operation.

        Returns None if no rule matches (default deny).
        """
        for rule in self.rules:
            if rule.ref == ref_id and op in rule.allow_ops:
                return rule
        return None
