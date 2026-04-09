"""Tests for policy evaluation.

Table-driven: each test case is a (catalog, standing, ref, op) -> expected decision.
"""

from __future__ import annotations

import pytest

from custody.catalog.schema import Catalog
from custody.enums import Decision, DenyReason, MediationMode, OperationKind
from custody.policy.eval import evaluate
from custody.policy.schema import Policy
from custody.standing.client import StandingError, StandingSummary


class TestPolicyEvaluation:
    def test_allow_prod_deploy_ssh(
        self, catalog: Catalog, policy: Policy, deployer_standing: StandingSummary
    ) -> None:
        result = evaluate(catalog, policy, deployer_standing, "ssh/prod/deploy", OperationKind.SSH)
        assert result.allowed
        assert result.ref_id == "ssh/prod/deploy"
        assert result.matched_rule is not None
        assert result.matched_rule.id == "allow-prod-deploy-ssh"

    def test_allow_staging_ops_ssh(
        self, catalog: Catalog, policy: Policy, operator_standing: StandingSummary
    ) -> None:
        result = evaluate(catalog, policy, operator_standing, "ssh/staging/ops", OperationKind.SSH)
        assert result.allowed

    def test_deny_ref_not_found(
        self, catalog: Catalog, policy: Policy, deployer_standing: StandingSummary
    ) -> None:
        result = evaluate(catalog, policy, deployer_standing, "ssh/prod/nonexistent", OperationKind.SSH)
        assert not result.allowed
        assert result.deny_reason == DenyReason.REF_NOT_FOUND

    def test_deny_missing_standing(
        self, catalog: Catalog, policy: Policy, missing_standing: StandingError
    ) -> None:
        result = evaluate(catalog, policy, missing_standing, "ssh/prod/deploy", OperationKind.SSH)
        assert not result.allowed
        assert result.deny_reason == DenyReason.MISSING_STANDING

    def test_deny_expired_standing(
        self, catalog: Catalog, policy: Policy, expired_standing: StandingSummary
    ) -> None:
        result = evaluate(catalog, policy, expired_standing, "ssh/prod/deploy", OperationKind.SSH)
        assert not result.allowed
        assert result.deny_reason == DenyReason.EXPIRED_STANDING

    def test_deny_wrong_role(
        self, catalog: Catalog, policy: Policy, operator_standing: StandingSummary
    ) -> None:
        # operator trying to use prod deploy (needs deployer role)
        result = evaluate(catalog, policy, operator_standing, "ssh/prod/deploy", OperationKind.SSH)
        assert not result.allowed
        assert result.deny_reason == DenyReason.INVALID_STANDING

    def test_deny_operation_not_allowed_on_ref(
        self, catalog: Catalog, policy: Policy, deployer_standing: StandingSummary
    ) -> None:
        # SSH ref doesn't allow sign
        result = evaluate(catalog, policy, deployer_standing, "ssh/prod/deploy", OperationKind.SIGN)
        assert not result.allowed
        assert result.deny_reason == DenyReason.OPERATION_NOT_ALLOWED

    def test_deny_unsupported_export(
        self, catalog: Catalog, policy: Policy, deployer_standing: StandingSummary
    ) -> None:
        result = evaluate(catalog, policy, deployer_standing, "ssh/prod/deploy", OperationKind.EXPORT)
        assert not result.allowed
        assert result.deny_reason == DenyReason.UNSUPPORTED_OPERATION

    def test_governor_required(
        self, catalog: Catalog, policy: Policy
    ) -> None:
        standing = StandingSummary(
            principal="eve",
            expires_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc)
            + __import__("datetime").timedelta(hours=1),
            claims={"role": "release-engineer"},
            attestation_id="att-005",
        )
        result = evaluate(catalog, policy, standing, "signing/release/macos", OperationKind.SIGN)
        assert not result.allowed
        assert result.deny_reason == DenyReason.GOVERNOR_REQUIRED
        assert result.mediation == MediationMode.GOVERNOR_REQUIRED

    def test_alias_resolves_to_canonical(
        self, catalog: Catalog, policy: Policy, operator_standing: StandingSummary
    ) -> None:
        result = evaluate(catalog, policy, operator_standing, "staging-ops", OperationKind.SSH)
        assert result.allowed
        assert result.ref_id == "ssh/staging/ops"

    def test_deny_no_matching_policy(
        self, catalog: Catalog, policy: Policy, deployer_standing: StandingSummary
    ) -> None:
        # deployer has right standing but signing ref has no policy for deployer role
        result = evaluate(catalog, policy, deployer_standing, "signing/release/macos", OperationKind.SIGN)
        assert not result.allowed
        assert result.deny_reason == DenyReason.INVALID_STANDING
