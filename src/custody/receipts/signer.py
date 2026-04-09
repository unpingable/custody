"""Receipt signing with Ed25519.

v0: generates an ephemeral signing key if none exists.
Future: key management integration.
"""

from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from custody.receipts.schema import Receipt


class ReceiptSigner:
    """Signs and verifies receipts with Ed25519."""

    def __init__(self, private_key: Ed25519PrivateKey) -> None:
        self._private_key = private_key
        self._public_key = private_key.public_key()

    @classmethod
    def generate(cls) -> ReceiptSigner:
        """Generate a new ephemeral signing key."""
        return cls(Ed25519PrivateKey.generate())

    @classmethod
    def from_file(cls, path: Path) -> ReceiptSigner:
        """Load a signing key from a PEM file."""
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        key_bytes = path.read_bytes()
        key = load_pem_private_key(key_bytes, password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise TypeError(f"Expected Ed25519 key, got {type(key)}")
        return cls(key)

    def save(self, path: Path) -> None:
        """Save the signing key to a PEM file."""
        pem = self._private_key.private_bytes(
            Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
        )
        path.write_bytes(pem)

    def sign(self, receipt: Receipt) -> Receipt:
        """Sign a receipt, returning a new Receipt with the signature field set."""
        hash_bytes = bytes.fromhex(receipt.receipt_hash)
        sig = self._private_key.sign(hash_bytes)
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
            receipt_hash=receipt.receipt_hash,
            signature=sig.hex(),
        )

    def verify(self, receipt: Receipt) -> bool:
        """Verify a receipt's signature."""
        try:
            hash_bytes = bytes.fromhex(receipt.receipt_hash)
            sig_bytes = bytes.fromhex(receipt.signature)
            self._public_key.verify(sig_bytes, hash_bytes)
            return True
        except Exception:
            return False

    @property
    def public_key(self) -> Ed25519PublicKey:
        return self._public_key

    def public_key_bytes(self) -> bytes:
        return self._public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
