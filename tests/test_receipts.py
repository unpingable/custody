"""Tests for receipt schema, serialization, signing, and chain verification."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from custody.enums import Decision, MaterializationMode, OperationKind
from custody.receipts.schema import GENESIS_MARKER, Receipt, build_receipt
from custody.receipts.signer import ReceiptSigner
from custody.receipts.log import ReceiptLog


class TestReceiptSchema:
    def test_genesis_marker_is_deterministic(self) -> None:
        import hashlib
        expected = hashlib.sha256(b"custody:genesis:v0").hexdigest()
        assert GENESIS_MARKER == expected

    def test_build_receipt(self) -> None:
        receipt = build_receipt(
            principal="alice",
            attestation_id="att-001",
            ref_id="ssh/prod/deploy",
            operation=OperationKind.SSH,
            target_context="host.example.com",
            policy_rule_id="allow-prod-deploy-ssh",
            governor_mediated=False,
            decision=Decision.ALLOW,
            reason="",
            lease_ttl_seconds=900,
            backend="ssh_agent",
            materialized=MaterializationMode.INDIRECT_USE,
            prev_receipt_hash=GENESIS_MARKER,
        )
        assert receipt.receipt_hash != ""
        assert receipt.prev_receipt_hash == GENESIS_MARKER

    def test_canonical_json_is_sorted(self) -> None:
        receipt = build_receipt(
            principal="alice",
            attestation_id="att-001",
            ref_id="ssh/prod/deploy",
            operation=OperationKind.SSH,
            target_context="host.example.com",
            policy_rule_id="allow-prod-deploy-ssh",
            governor_mediated=False,
            decision=Decision.ALLOW,
            reason="",
            lease_ttl_seconds=900,
            backend="ssh_agent",
            materialized=MaterializationMode.INDIRECT_USE,
            prev_receipt_hash=GENESIS_MARKER,
        )
        canonical = json.loads(receipt.canonical_json())
        keys = list(canonical.keys())
        assert keys == sorted(keys)

    def test_receipt_hash_matches_recompute(self) -> None:
        receipt = build_receipt(
            principal="alice",
            attestation_id="att-001",
            ref_id="ssh/prod/deploy",
            operation=OperationKind.SSH,
            target_context="host.example.com",
            policy_rule_id="allow-prod-deploy-ssh",
            governor_mediated=False,
            decision=Decision.ALLOW,
            reason="",
            lease_ttl_seconds=900,
            backend="ssh_agent",
            materialized=MaterializationMode.INDIRECT_USE,
            prev_receipt_hash=GENESIS_MARKER,
        )
        assert receipt.receipt_hash == receipt.compute_hash()


class TestReceiptSigning:
    def test_sign_and_verify(self) -> None:
        signer = ReceiptSigner.generate()
        receipt = build_receipt(
            principal="alice",
            attestation_id="att-001",
            ref_id="ssh/prod/deploy",
            operation=OperationKind.SSH,
            target_context="host.example.com",
            policy_rule_id="allow-prod-deploy-ssh",
            governor_mediated=False,
            decision=Decision.ALLOW,
            reason="",
            lease_ttl_seconds=900,
            backend="ssh_agent",
            materialized=MaterializationMode.INDIRECT_USE,
            prev_receipt_hash=GENESIS_MARKER,
        )
        signed = signer.sign(receipt)
        assert signed.signature != ""
        assert signer.verify(signed)

    def test_tampered_receipt_fails_verification(self) -> None:
        signer = ReceiptSigner.generate()
        receipt = build_receipt(
            principal="alice",
            attestation_id="att-001",
            ref_id="ssh/prod/deploy",
            operation=OperationKind.SSH,
            target_context="host.example.com",
            policy_rule_id="allow-prod-deploy-ssh",
            governor_mediated=False,
            decision=Decision.ALLOW,
            reason="",
            lease_ttl_seconds=900,
            backend="ssh_agent",
            materialized=MaterializationMode.INDIRECT_USE,
            prev_receipt_hash=GENESIS_MARKER,
        )
        signed = signer.sign(receipt)
        # Tamper: change the receipt_hash
        tampered = Receipt(
            receipt_id=signed.receipt_id,
            timestamp=signed.timestamp,
            principal=signed.principal,
            attestation_id=signed.attestation_id,
            ref_id=signed.ref_id,
            operation=signed.operation,
            target_context=signed.target_context,
            policy_rule_id=signed.policy_rule_id,
            governor_mediated=signed.governor_mediated,
            decision=signed.decision,
            reason=signed.reason,
            lease_ttl_seconds=signed.lease_ttl_seconds,
            backend=signed.backend,
            materialized=signed.materialized,
            prev_receipt_hash=signed.prev_receipt_hash,
            receipt_hash="0000000000000000000000000000000000000000000000000000000000000000",
            signature=signed.signature,
        )
        assert not signer.verify(tampered)


class TestReceiptLog:
    def test_append_and_read(self, tmp_path: Path) -> None:
        signer = ReceiptSigner.generate()
        log = ReceiptLog(tmp_path / "receipts.jsonl", signer)

        receipt = build_receipt(
            principal="alice",
            attestation_id="att-001",
            ref_id="ssh/prod/deploy",
            operation=OperationKind.SSH,
            target_context="host.example.com",
            policy_rule_id="allow-prod-deploy-ssh",
            governor_mediated=False,
            decision=Decision.ALLOW,
            reason="",
            lease_ttl_seconds=900,
            backend="ssh_agent",
            materialized=MaterializationMode.INDIRECT_USE,
            prev_receipt_hash=log.prev_receipt_hash,
        )
        log.append(receipt)

        receipts = log.read_all()
        assert len(receipts) == 1
        assert receipts[0].principal == "alice"

    def test_chain_verification(self, tmp_path: Path) -> None:
        signer = ReceiptSigner.generate()
        log = ReceiptLog(tmp_path / "receipts.jsonl", signer)

        for i in range(3):
            receipt = build_receipt(
                principal=f"user-{i}",
                attestation_id=f"att-{i:03d}",
                ref_id="ssh/prod/deploy",
                operation=OperationKind.SSH,
                target_context="host.example.com",
                policy_rule_id="allow-prod-deploy-ssh",
                governor_mediated=False,
                decision=Decision.ALLOW,
                reason="",
                lease_ttl_seconds=900,
                backend="ssh_agent",
                materialized=MaterializationMode.INDIRECT_USE,
                prev_receipt_hash=log.prev_receipt_hash,
            )
            log.append(receipt)

        valid, msg = log.verify_chain()
        assert valid
        assert "3 receipts" in msg

    def test_broken_chain_detected(self, tmp_path: Path) -> None:
        signer = ReceiptSigner.generate()
        log = ReceiptLog(tmp_path / "receipts.jsonl", signer)

        receipt = build_receipt(
            principal="alice",
            attestation_id="att-001",
            ref_id="ssh/prod/deploy",
            operation=OperationKind.SSH,
            target_context="host.example.com",
            policy_rule_id="allow-prod-deploy-ssh",
            governor_mediated=False,
            decision=Decision.ALLOW,
            reason="",
            lease_ttl_seconds=900,
            backend="ssh_agent",
            materialized=MaterializationMode.INDIRECT_USE,
            prev_receipt_hash=log.prev_receipt_hash,
        )
        log.append(receipt)

        # Tamper with the log file
        log_path = tmp_path / "receipts.jsonl"
        lines = log_path.read_text().strip().splitlines()
        data = json.loads(lines[0])
        data["principal"] = "TAMPERED"
        log_path.write_text(json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n")

        valid, msg = log.verify_chain()
        assert not valid

    def test_wrong_prev_hash_rejected(self, tmp_path: Path) -> None:
        signer = ReceiptSigner.generate()
        log = ReceiptLog(tmp_path / "receipts.jsonl", signer)

        receipt = build_receipt(
            principal="alice",
            attestation_id="att-001",
            ref_id="ssh/prod/deploy",
            operation=OperationKind.SSH,
            target_context="host.example.com",
            policy_rule_id="allow-prod-deploy-ssh",
            governor_mediated=False,
            decision=Decision.ALLOW,
            reason="",
            lease_ttl_seconds=900,
            backend="ssh_agent",
            materialized=MaterializationMode.INDIRECT_USE,
            prev_receipt_hash="wrong_hash",
        )
        with pytest.raises(ValueError, match="Chain broken"):
            log.append(receipt)
