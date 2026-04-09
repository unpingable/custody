"""Load a catalog from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from custody.catalog.schema import Catalog, Ref, Selector
from custody.enums import BackendKind, OperationKind, RefClass, SelectorKind


def _parse_selectors(raw: dict[str, str]) -> tuple[Selector, ...]:
    selectors = []
    for kind_str, value in raw.items():
        kind = SelectorKind(kind_str)
        selectors.append(Selector(kind=kind, value=value))
    return tuple(selectors)


def _parse_ref(raw: dict[str, Any]) -> Ref:
    return Ref(
        id=raw["id"],
        ref_class=RefClass(raw["class"]),
        backend=BackendKind(raw["backend"].replace("-", "_")),
        selectors=_parse_selectors(raw.get("selector", {})),
        owner=raw.get("owner", ""),
        scope=raw.get("scope", ""),
        allowed_ops=frozenset(OperationKind(op) for op in raw.get("allowed_ops", [])),
        lease_ttl_seconds=raw.get("lease_ttl_seconds", 900),
        break_glass=raw.get("break_glass", False),
        rotation_hint=raw.get("rotation_hint", "manual"),
        aliases=tuple(raw.get("aliases", [])),
    )


def load_catalog(path: Path) -> Catalog:
    """Load a catalog from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)

    catalog = Catalog()
    for raw_ref in data.get("refs", []):
        ref = _parse_ref(raw_ref)
        catalog.add(ref)
    return catalog
