"""Canonical enums for the Custody model.

These are compatibility-sensitive. Changes require updating goldens.
"""

from __future__ import annotations

from enum import Enum


class RefClass(str, Enum):
    SSH = "ssh"
    SIGNING = "signing"
    REPO_TOKEN = "repo_token"
    DECRYPT_KEY = "decrypt_key"
    LEASE = "lease"

    @classmethod
    def _missing_(cls, value: object) -> RefClass | None:
        return None


class BackendKind(str, Enum):
    SSH_AGENT = "ssh_agent"
    AGE = "age"
    SOPS = "sops"
    FILE_HANDLE = "file_handle"
    ENV_HANDLE = "env_handle"


class OperationKind(str, Enum):
    SSH = "ssh"
    SIGN = "sign"
    DECRYPT = "decrypt"
    MINT = "mint"
    EXPORT = "export"  # reserved; unsupported in v0

    V0_SUPPORTED = frozenset({"ssh"})  # type: ignore[assignment]


# Actually define supported ops as a module-level constant
V0_SUPPORTED_OPS: frozenset[str] = frozenset({"ssh"})


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class DenyReason(str, Enum):
    MISSING_STANDING = "missing_standing"
    INVALID_STANDING = "invalid_standing"
    EXPIRED_STANDING = "expired_standing"
    REF_NOT_FOUND = "ref_not_found"
    ALIAS_UNRESOLVED = "alias_unresolved"
    NO_MATCHING_POLICY = "no_matching_policy"
    OPERATION_NOT_ALLOWED = "operation_not_allowed"
    GOVERNOR_REQUIRED = "governor_required"
    GOVERNOR_DENIED = "governor_denied"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    SELECTOR_MISMATCH = "selector_mismatch"
    AMBIGUOUS_SELECTOR = "ambiguous_selector"
    RECEIPT_FAILURE = "receipt_failure"
    BREAK_GLASS_REQUIRED = "break_glass_required"
    UNSUPPORTED_OPERATION = "unsupported_operation"


class MediationMode(str, Enum):
    LOCAL_POLICY_ONLY = "local_policy_only"
    GOVERNOR_REQUIRED = "governor_required"


class MaterializationMode(str, Enum):
    INDIRECT_USE = "indirect_use"
    MATERIALIZED = "materialized"


class ReceiptOutcome(str, Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    ALLOWED_BUT_RECEIPT_SUSPECT = "allowed_but_receipt_suspect"


class SelectorKind(str, Enum):
    FINGERPRINT = "fingerprint"
    COMMENT = "comment"
    KEYGRIP = "keygrip"
    PATH = "path"
    OPAQUE_HANDLE = "opaque_handle"
