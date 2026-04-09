"""Shared test fixtures."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from custody.catalog.loader import load_catalog
from custody.catalog.schema import Catalog
from custody.policy.loader import load_policy
from custody.policy.schema import Policy
from custody.standing.client import StandingError, StandingSummary

GOLDENS_DIR = Path(__file__).parent / "goldens"


@pytest.fixture
def catalog() -> Catalog:
    return load_catalog(GOLDENS_DIR / "catalog.yaml")


@pytest.fixture
def policy() -> Policy:
    return load_policy(GOLDENS_DIR / "policy.yaml")


@pytest.fixture
def deployer_standing() -> StandingSummary:
    return StandingSummary(
        principal="alice",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        claims={"role": "deployer", "env": "prod"},
        attestation_id="att-001",
    )


@pytest.fixture
def operator_standing() -> StandingSummary:
    return StandingSummary(
        principal="bob",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        claims={"role": "operator", "env": "staging"},
        attestation_id="att-002",
    )


@pytest.fixture
def expired_standing() -> StandingSummary:
    return StandingSummary(
        principal="carol",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        claims={"role": "deployer", "env": "prod"},
        attestation_id="att-003",
    )


@pytest.fixture
def missing_standing() -> StandingError:
    return StandingError(code="missing", message="No standing token provided")
