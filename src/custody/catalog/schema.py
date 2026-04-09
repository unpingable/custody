"""Ref catalog schema.

A ref is a metadata handle to sensitive material. It is never the bytes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from custody.enums import BackendKind, OperationKind, RefClass, SelectorKind

REF_ID_PATTERN = re.compile(
    r"^[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*(?:@[A-Za-z0-9._-]+)?$"
)


@dataclass(frozen=True)
class Selector:
    """Identifies material by public metadata, never by the bytes themselves."""

    kind: SelectorKind
    value: str


@dataclass(frozen=True)
class Ref:
    """A named handle to sensitive material plus metadata and policy."""

    id: str
    ref_class: RefClass
    backend: BackendKind
    selectors: tuple[Selector, ...]
    owner: str
    scope: str
    allowed_ops: frozenset[OperationKind]
    lease_ttl_seconds: int = 900
    break_glass: bool = False
    rotation_hint: str = "manual"
    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not REF_ID_PATTERN.match(self.id):
            raise ValueError(f"Invalid ref id: {self.id!r}")
        if self.lease_ttl_seconds <= 0:
            raise ValueError(f"Lease TTL must be > 0, got {self.lease_ttl_seconds}")
        if self.lease_ttl_seconds > 3600:
            raise ValueError(
                f"Lease TTL must be <= 3600 in v0, got {self.lease_ttl_seconds}"
            )


@dataclass
class Catalog:
    """Collection of refs with alias resolution."""

    refs: dict[str, Ref] = field(default_factory=dict)
    _aliases: dict[str, str] = field(default_factory=dict)

    def add(self, ref: Ref) -> None:
        if ref.id in self.refs:
            raise ValueError(f"Duplicate ref id: {ref.id!r}")
        for alias in ref.aliases:
            if alias in self._aliases:
                raise ValueError(
                    f"Alias {alias!r} already maps to {self._aliases[alias]!r}"
                )
            if alias in self.refs:
                raise ValueError(f"Alias {alias!r} collides with ref id")
            self._aliases[alias] = ref.id
        self.refs[ref.id] = ref

    def resolve(self, name: str) -> Ref | None:
        """Resolve a ref id or alias to a Ref. Returns None if not found."""
        if name in self.refs:
            return self.refs[name]
        canonical = self._aliases.get(name)
        if canonical is not None:
            return self.refs.get(canonical)
        return None
