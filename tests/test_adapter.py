"""Tests for the fake adapter (dry-run goldens)."""

from __future__ import annotations

from custody.adapters.fake import FakeAdapter
from custody.adapters.ssh_agent import SshAgentKey
from custody.catalog.schema import Ref, Selector
from custody.enums import BackendKind, OperationKind, RefClass, SelectorKind


def _make_ref(fingerprint: str = "SHA256:abc123", comment: str = "deploy@prod") -> Ref:
    return Ref(
        id="ssh/prod/deploy",
        ref_class=RefClass.SSH,
        backend=BackendKind.SSH_AGENT,
        selectors=(
            Selector(SelectorKind.FINGERPRINT, fingerprint),
            Selector(SelectorKind.COMMENT, comment),
        ),
        owner="platform",
        scope="prod",
        allowed_ops=frozenset({OperationKind.SSH}),
    )


def _make_key(fingerprint: str = "SHA256:abc123", comment: str = "deploy@prod") -> SshAgentKey:
    return SshAgentKey(bits="256", fingerprint=fingerprint, comment=comment, key_type="ED25519")


class TestFakeAdapter:
    def test_resolve_success(self) -> None:
        adapter = FakeAdapter(keys=[_make_key()])
        ref = _make_ref()
        key = adapter.resolve_selector(ref)
        assert key is not None
        assert key.fingerprint == "SHA256:abc123"

    def test_resolve_no_keys(self) -> None:
        adapter = FakeAdapter(keys=[])
        ref = _make_ref()
        assert adapter.resolve_selector(ref) is None

    def test_resolve_selector_mismatch(self) -> None:
        adapter = FakeAdapter(keys=[_make_key(fingerprint="SHA256:other")])
        ref = _make_ref(fingerprint="SHA256:abc123")
        # comment still matches, so one match
        key = adapter.resolve_selector(ref)
        # Both selectors checked: fingerprint mismatches but comment might match
        # The key has comment "deploy@prod" and ref selector has comment "deploy@prod"
        # So there IS a match on comment
        assert key is not None

    def test_resolve_ambiguous(self) -> None:
        # Two keys match the same selector
        adapter = FakeAdapter(keys=[
            _make_key(fingerprint="SHA256:abc123", comment="deploy@prod"),
            _make_key(fingerprint="SHA256:abc123", comment="deploy@prod-2"),
        ])
        ref = _make_ref()
        # fingerprint matches both, comment matches first only
        # Actually: selector has both fingerprint and comment
        # Key 1: fingerprint matches -> added, comment matches -> added (2 matches)
        # So it's ambiguous
        key = adapter.resolve_selector(ref)
        assert key is None

    def test_dispatch_records_call(self) -> None:
        adapter = FakeAdapter(keys=[_make_key()])
        key = _make_key()
        result = adapter.dispatch_ssh("host.example.com", key)
        assert result.success
        assert len(adapter.dispatch_calls) == 1
        assert adapter.dispatch_calls[0] == ("host.example.com", key)
