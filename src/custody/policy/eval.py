"""Policy evaluation.

Evaluation order:
1. resolve ref
2. verify standing
3. match policy
4. deny by default
5. if matched and governor: true, require Governor decision
6. dispatch if allowed
7. emit receipt
"""

from __future__ import annotations

from dataclasses import dataclass

from custody.catalog.schema import Catalog
from custody.enums import (
    Decision,
    DenyReason,
    MediationMode,
    OperationKind,
)
from custody.policy.schema import Policy, PolicyRule
from custody.standing.client import StandingError, StandingSummary


@dataclass(frozen=True)
class DecisionResult:
    """The result of a policy evaluation."""

    decision: Decision
    ref_id: str
    operation: OperationKind
    deny_reason: DenyReason | None = None
    matched_rule: PolicyRule | None = None
    mediation: MediationMode = MediationMode.LOCAL_POLICY_ONLY

    @property
    def allowed(self) -> bool:
        return self.decision == Decision.ALLOW


def _deny(ref_id: str, op: OperationKind, reason: DenyReason) -> DecisionResult:
    return DecisionResult(
        decision=Decision.DENY,
        ref_id=ref_id,
        operation=op,
        deny_reason=reason,
    )


def evaluate(
    catalog: Catalog,
    policy: Policy,
    standing: StandingSummary | StandingError,
    ref_name: str,
    operation: OperationKind,
) -> DecisionResult:
    """Evaluate a policy decision for an operation on a ref."""

    # Export is never allowed
    if operation == OperationKind.EXPORT:
        return _deny(ref_name, operation, DenyReason.UNSUPPORTED_OPERATION)

    # Resolve ref
    ref = catalog.resolve(ref_name)
    if ref is None:
        return _deny(ref_name, operation, DenyReason.REF_NOT_FOUND)
    canonical_id = ref.id

    # Verify standing
    if isinstance(standing, StandingError):
        reason_map = {
            "missing": DenyReason.MISSING_STANDING,
            "invalid": DenyReason.INVALID_STANDING,
            "expired": DenyReason.EXPIRED_STANDING,
        }
        return _deny(
            canonical_id,
            operation,
            reason_map.get(standing.code, DenyReason.INVALID_STANDING),
        )

    if standing.is_expired:
        return _deny(canonical_id, operation, DenyReason.EXPIRED_STANDING)

    # Check if operation is allowed on the ref
    if operation not in ref.allowed_ops:
        return _deny(canonical_id, operation, DenyReason.OPERATION_NOT_ALLOWED)

    # Match policy (always against canonical ref id)
    rule = policy.match(canonical_id, operation)
    if rule is None:
        return _deny(canonical_id, operation, DenyReason.NO_MATCHING_POLICY)

    # Check standing claims against policy requirements
    for key, required_value in rule.require_standing.claims.items():
        actual = standing.claims.get(key)
        if actual != required_value:
            return _deny(canonical_id, operation, DenyReason.INVALID_STANDING)

    # Governor mediation
    if rule.governor:
        return DecisionResult(
            decision=Decision.DENY,
            ref_id=canonical_id,
            operation=operation,
            deny_reason=DenyReason.GOVERNOR_REQUIRED,
            matched_rule=rule,
            mediation=MediationMode.GOVERNOR_REQUIRED,
        )

    # Allow
    return DecisionResult(
        decision=Decision.ALLOW,
        ref_id=canonical_id,
        operation=operation,
        matched_rule=rule,
        mediation=MediationMode.LOCAL_POLICY_ONLY,
    )
