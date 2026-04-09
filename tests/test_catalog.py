"""Tests for catalog schema and loading."""

from __future__ import annotations

import pytest

from custody.catalog.schema import Catalog, Ref, Selector
from custody.enums import BackendKind, OperationKind, RefClass, SelectorKind


class TestRefValidation:
    def test_valid_ref(self) -> None:
        ref = Ref(
            id="ssh/prod/deploy",
            ref_class=RefClass.SSH,
            backend=BackendKind.SSH_AGENT,
            selectors=(Selector(SelectorKind.FINGERPRINT, "SHA256:abc"),),
            owner="platform",
            scope="prod",
            allowed_ops=frozenset({OperationKind.SSH}),
        )
        assert ref.id == "ssh/prod/deploy"

    def test_invalid_ref_id(self) -> None:
        with pytest.raises(ValueError, match="Invalid ref id"):
            Ref(
                id="INVALID",
                ref_class=RefClass.SSH,
                backend=BackendKind.SSH_AGENT,
                selectors=(),
                owner="",
                scope="",
                allowed_ops=frozenset(),
            )

    def test_ref_id_with_spaces(self) -> None:
        with pytest.raises(ValueError, match="Invalid ref id"):
            Ref(
                id="ssh/prod/deploy key",
                ref_class=RefClass.SSH,
                backend=BackendKind.SSH_AGENT,
                selectors=(),
                owner="",
                scope="",
                allowed_ops=frozenset(),
            )

    def test_ttl_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="must be > 0"):
            Ref(
                id="ssh/prod/deploy",
                ref_class=RefClass.SSH,
                backend=BackendKind.SSH_AGENT,
                selectors=(),
                owner="",
                scope="",
                allowed_ops=frozenset(),
                lease_ttl_seconds=0,
            )

    def test_ttl_max_3600(self) -> None:
        with pytest.raises(ValueError, match="<= 3600"):
            Ref(
                id="ssh/prod/deploy",
                ref_class=RefClass.SSH,
                backend=BackendKind.SSH_AGENT,
                selectors=(),
                owner="",
                scope="",
                allowed_ops=frozenset(),
                lease_ttl_seconds=7200,
            )

    def test_ref_with_version(self) -> None:
        ref = Ref(
            id="ssh/prod/deploy@v2",
            ref_class=RefClass.SSH,
            backend=BackendKind.SSH_AGENT,
            selectors=(),
            owner="",
            scope="",
            allowed_ops=frozenset(),
        )
        assert ref.id == "ssh/prod/deploy@v2"


class TestCatalog:
    def test_duplicate_ref_id(self) -> None:
        catalog = Catalog()
        ref = Ref(
            id="ssh/prod/deploy",
            ref_class=RefClass.SSH,
            backend=BackendKind.SSH_AGENT,
            selectors=(),
            owner="",
            scope="",
            allowed_ops=frozenset(),
        )
        catalog.add(ref)
        with pytest.raises(ValueError, match="Duplicate ref id"):
            catalog.add(ref)

    def test_alias_resolution(self) -> None:
        catalog = Catalog()
        ref = Ref(
            id="ssh/prod/deploy",
            ref_class=RefClass.SSH,
            backend=BackendKind.SSH_AGENT,
            selectors=(),
            owner="",
            scope="",
            allowed_ops=frozenset(),
            aliases=("prod-deploy",),
        )
        catalog.add(ref)
        assert catalog.resolve("prod-deploy") is ref
        assert catalog.resolve("ssh/prod/deploy") is ref

    def test_alias_collision(self) -> None:
        catalog = Catalog()
        ref1 = Ref(
            id="ssh/prod/deploy",
            ref_class=RefClass.SSH,
            backend=BackendKind.SSH_AGENT,
            selectors=(),
            owner="",
            scope="",
            allowed_ops=frozenset(),
            aliases=("shared-alias",),
        )
        ref2 = Ref(
            id="ssh/staging/deploy",
            ref_class=RefClass.SSH,
            backend=BackendKind.SSH_AGENT,
            selectors=(),
            owner="",
            scope="",
            allowed_ops=frozenset(),
            aliases=("shared-alias",),
        )
        catalog.add(ref1)
        with pytest.raises(ValueError, match="already maps to"):
            catalog.add(ref2)

    def test_resolve_not_found(self) -> None:
        catalog = Catalog()
        assert catalog.resolve("nonexistent") is None


class TestCatalogLoader:
    def test_load_golden_catalog(self, catalog: Catalog) -> None:
        assert "ssh/prod/deploy" in catalog.refs
        assert "ssh/staging/ops" in catalog.refs
        assert "signing/release/macos" in catalog.refs

    def test_alias_in_loaded_catalog(self, catalog: Catalog) -> None:
        ref = catalog.resolve("staging-ops")
        assert ref is not None
        assert ref.id == "ssh/staging/ops"
