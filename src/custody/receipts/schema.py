"""Receipt schema.

Wire format is frozen for v0:
- Canonical JSON (sorted keys, no extra whitespace, UTF-8)
- SHA-256 for hash chain
- Ed25519 for signatures
- Genesis: SHA-256("custody:genesis:v0")
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from custody.enums import (
    Decision,
    DenyReason,
    MaterializationMode,
    MediationMode,
    OperationKind,
    ReceiptOutcome,
)

GENESIS_MARKER = hashlib.sha256(b"custody:genesis:v0").hexdigest()


@dataclass(frozen=True)
class Receipt:
    """A single receipt in the append-only chain."""

    receipt_id: str
    timestamp: str  # ISO 8601 UTC
    principal: str
    attestation_id: str
    ref_id: str
    operation: str
    target_context: str
    policy_rule_id: str
    governor_mediated: bool
    decision: str
    reason: str
    lease_ttl_seconds: int
    backend: str
    materialized: str
    prev_receipt_hash: str
    receipt_hash: str = ""
    signature: str = ""

    def canonical_dict(self) -> dict:
        """Return the receipt as a dict for canonical serialization.

        Excludes receipt_hash and signature (those are computed over this).
        """
        return {
            "receipt_id": self.receipt_id,
            "timestamp": self.timestamp,
            "principal": self.principal,
            "attestation_id": self.attestation_id,
            "ref_id": self.ref_id,
            "operation": self.operation,
            "target_context": self.target_context,
            "policy_rule_id": self.policy_rule_id,
            "governor_mediated": self.governor_mediated,
            "decision": self.decision,
            "reason": self.reason,
            "lease_ttl_seconds": self.lease_ttl_seconds,
            "backend": self.backend,
            "materialized": self.materialized,
            "prev_receipt_hash": self.prev_receipt_hash,
        }

    def canonical_json(self) -> bytes:
        """Canonical JSON: sorted keys, no extra whitespace, UTF-8."""
        return json.dumps(
            self.canonical_dict(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")

    def compute_hash(self) -> str:
        """SHA-256 of the canonical JSON."""
        return hashlib.sha256(self.canonical_json()).hexdigest()


def build_receipt(
    principal: str,
    attestation_id: str,
    ref_id: str,
    operation: OperationKind,
    target_context: str,
    policy_rule_id: str,
    governor_mediated: bool,
    decision: Decision,
    reason: str,
    lease_ttl_seconds: int,
    backend: str,
    materialized: MaterializationMode,
    prev_receipt_hash: str,
) -> Receipt:
    """Build a receipt with computed hash. Signature is added by the signer."""
    receipt = Receipt(
        receipt_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        principal=principal,
        attestation_id=attestation_id,
        ref_id=ref_id,
        operation=operation.value,
        target_context=target_context,
        policy_rule_id=policy_rule_id,
        governor_mediated=governor_mediated,
        decision=decision.value,
        reason=reason,
        lease_ttl_seconds=lease_ttl_seconds,
        backend=backend,
        materialized=materialized.value,
        prev_receipt_hash=prev_receipt_hash,
    )
    receipt_hash = receipt.compute_hash()
    return Receipt(
        receipt_id=receipt.receipt_id,
        timestamp=receipt.timestamp,
        principal=receipt.principal,
        attestation_id=receipt.attestation_id,
        ref_id=receipt.ref_id,
        operation=receipt.operation,
        target_context=receipt.target_context,
        policy_rule_id=receipt.policy_rule_id,
        governor_mediated=receipt.governor_mediated,
        decision=receipt.decision,
        reason=receipt.reason,
        lease_ttl_seconds=receipt.lease_ttl_seconds,
        backend=receipt.backend,
        materialized=receipt.materialized,
        prev_receipt_hash=receipt.prev_receipt_hash,
        receipt_hash=receipt_hash,
    )
