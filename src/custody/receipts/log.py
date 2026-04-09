"""Append-only receipt log.

Receipts are stored as newline-delimited JSON, one receipt per line.
The chain is verified by checking prev_receipt_hash linkage and signatures.
"""

from __future__ import annotations

import json
from pathlib import Path

from custody.receipts.schema import GENESIS_MARKER, Receipt
from custody.receipts.signer import ReceiptSigner


class ReceiptLog:
    """Append-only, hash-chained receipt log backed by a local file."""

    def __init__(self, path: Path, signer: ReceiptSigner) -> None:
        self._path = path
        self._signer = signer
        self._last_hash = self._read_last_hash()

    def _read_last_hash(self) -> str:
        """Read the hash of the last receipt in the log, or genesis."""
        if not self._path.exists():
            return GENESIS_MARKER
        lines = self._path.read_text().strip().splitlines()
        if not lines:
            return GENESIS_MARKER
        last = json.loads(lines[-1])
        return last["receipt_hash"]

    @property
    def prev_receipt_hash(self) -> str:
        return self._last_hash

    def append(self, receipt: Receipt) -> Receipt:
        """Sign and append a receipt to the log. Returns the signed receipt."""
        if receipt.prev_receipt_hash != self._last_hash:
            raise ValueError(
                f"Chain broken: expected prev_receipt_hash={self._last_hash!r}, "
                f"got {receipt.prev_receipt_hash!r}"
            )
        signed = self._signer.sign(receipt)
        line = json.dumps(
            {**signed.canonical_dict(), "receipt_hash": signed.receipt_hash, "signature": signed.signature},
            sort_keys=True,
            separators=(",", ":"),
        )
        with open(self._path, "a") as f:
            f.write(line + "\n")
        self._last_hash = signed.receipt_hash
        return signed

    def read_all(self) -> list[Receipt]:
        """Read all receipts from the log."""
        if not self._path.exists():
            return []
        receipts = []
        for line in self._path.read_text().strip().splitlines():
            data = json.loads(line)
            receipts.append(Receipt(**data))
        return receipts

    def verify_chain(self) -> tuple[bool, str]:
        """Verify the entire receipt chain. Returns (valid, message)."""
        receipts = self.read_all()
        if not receipts:
            return True, "Empty log"

        expected_prev = GENESIS_MARKER
        for i, receipt in enumerate(receipts):
            if receipt.prev_receipt_hash != expected_prev:
                return False, f"Receipt {i}: prev_receipt_hash mismatch"

            recomputed = receipt.compute_hash()
            if receipt.receipt_hash != recomputed:
                return False, f"Receipt {i}: receipt_hash mismatch"

            if not self._signer.verify(receipt):
                return False, f"Receipt {i}: signature verification failed"

            expected_prev = receipt.receipt_hash

        return True, f"Chain valid: {len(receipts)} receipts"
