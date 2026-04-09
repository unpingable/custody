"""SSH agent adapter.

v0 semantics (frozen): resolve + authorize + shell out.
The adapter is deliberately stupid.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

from custody.catalog.schema import Ref
from custody.enums import SelectorKind


@dataclass(frozen=True)
class SshAgentKey:
    """A key listed by ssh-agent."""

    bits: str
    fingerprint: str
    comment: str
    key_type: str


@dataclass(frozen=True)
class AdapterResult:
    """Structured outcome from an adapter operation."""

    success: bool
    exit_code: int | None = None
    error: str = ""


def list_agent_keys() -> list[SshAgentKey]:
    """List keys from the running ssh-agent."""
    agent_sock = os.environ.get("SSH_AUTH_SOCK")
    if not agent_sock:
        return []

    try:
        result = subprocess.run(
            ["ssh-add", "-l"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    if result.returncode != 0:
        return []

    keys = []
    for line in result.stdout.strip().splitlines():
        parts = line.split(None, 3)
        if len(parts) >= 3:
            keys.append(SshAgentKey(
                bits=parts[0],
                fingerprint=parts[1],
                comment=parts[2] if len(parts) > 2 else "",
                key_type=parts[3].strip("()") if len(parts) > 3 else "",
            ))
    return keys


def resolve_selector(ref: Ref) -> SshAgentKey | None:
    """Resolve a ref's selector against ssh-agent keys.

    Returns the matching key, or None if no match / ambiguous.
    """
    agent_keys = list_agent_keys()
    if not agent_keys:
        return None

    matched_indices: set[int] = set()
    for selector in ref.selectors:
        for i, key in enumerate(agent_keys):
            if selector.kind == SelectorKind.FINGERPRINT and key.fingerprint == selector.value:
                matched_indices.add(i)
            elif selector.kind == SelectorKind.COMMENT and key.comment == selector.value:
                matched_indices.add(i)

    # Ambiguous or no match: return None (will result in deny)
    if len(matched_indices) != 1:
        return None
    return agent_keys[next(iter(matched_indices))]


def dispatch_ssh(target: str, key: SshAgentKey) -> AdapterResult:
    """Shell out to ssh with the resolved key identity.

    This is deliberately minimal. No PTY, no multiplexing, no brokering.
    """
    try:
        result = subprocess.run(
            ["ssh", "-o", "IdentitiesOnly=yes", target],
            timeout=300,
        )
        return AdapterResult(success=result.returncode == 0, exit_code=result.returncode)
    except subprocess.TimeoutExpired:
        return AdapterResult(success=False, error="SSH connection timed out")
    except FileNotFoundError:
        return AdapterResult(success=False, error="ssh binary not found")
