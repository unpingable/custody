"""Tests for enum stability and serialization."""

from __future__ import annotations

from custody.enums import (
    Decision,
    DenyReason,
    OperationKind,
    RefClass,
    V0_SUPPORTED_OPS,
)


class TestEnumSerialization:
    def test_enums_serialize_as_lowercase_strings(self) -> None:
        assert Decision.ALLOW.value == "allow"
        assert Decision.DENY.value == "deny"
        assert RefClass.SSH.value == "ssh"
        assert DenyReason.MISSING_STANDING.value == "missing_standing"

    def test_export_unsupported_in_v0(self) -> None:
        assert OperationKind.EXPORT.value not in V0_SUPPORTED_OPS

    def test_ssh_supported_in_v0(self) -> None:
        assert OperationKind.SSH.value in V0_SUPPORTED_OPS
