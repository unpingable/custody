"""Standing verification client.

Frozen contract for v0. Policy evaluates against claims.
Receipts log principal, attestation_id, and expires_at.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class StandingSummary:
    """Verified standing for a caller."""

    principal: str
    expires_at: datetime
    claims: dict[str, str]
    attestation_id: str

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at


@dataclass(frozen=True)
class StandingError:
    """Standing verification failure."""

    code: str  # missing | invalid | expired | unreachable
    message: str


def verify(token: str) -> StandingSummary | StandingError:
    """Verify a standing token.

    v0 stub: returns StandingError. Real implementation will call Standing service.
    """
    if not token:
        return StandingError(code="missing", message="No standing token provided")
    return StandingError(code="unreachable", message="Standing service not configured")
