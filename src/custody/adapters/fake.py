"""Fake adapter for testing.

Provides deterministic behavior without requiring a live ssh-agent.
"""

from __future__ import annotations

from custody.adapters.ssh_agent import AdapterResult, SshAgentKey
from custody.catalog.schema import Ref
from custody.enums import SelectorKind


class FakeAdapter:
    """A fake SSH adapter backed by a fixture key list."""

    def __init__(self, keys: list[SshAgentKey] | None = None) -> None:
        self.keys = keys or []
        self.dispatch_calls: list[tuple[str, SshAgentKey]] = []

    def resolve_selector(self, ref: Ref) -> SshAgentKey | None:
        matched_keys: set[int] = set()  # track by index to dedup
        for selector in ref.selectors:
            for i, key in enumerate(self.keys):
                if selector.kind == SelectorKind.FINGERPRINT and key.fingerprint == selector.value:
                    matched_keys.add(i)
                elif selector.kind == SelectorKind.COMMENT and key.comment == selector.value:
                    matched_keys.add(i)
        if len(matched_keys) != 1:
            return None
        return self.keys[next(iter(matched_keys))]

    def dispatch_ssh(self, target: str, key: SshAgentKey) -> AdapterResult:
        self.dispatch_calls.append((target, key))
        return AdapterResult(success=True, exit_code=0)
