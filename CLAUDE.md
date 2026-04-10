# CLAUDE.md — Instructions for Claude Code

## What This Is

custody: Chain-of-custody control surface for sensitive refs — secrets, keys, signing material, leases.

## What This Is Not

- Not a vault or secret store — Custody never owns the bytes
- Not an identity system — that's Standing
- Not a governance engine — that's Governor
- Not a session manager — that's Continuity

## Invariants

1. Refs are metadata handles, never secret bytes — the catalog must not contain raw material
2. Default deny — missing/invalid standing, no policy match, ambiguous selector all result in deny
3. Operation-not-blob — `get_bytes()` is not a public abstraction; v0 supports mediated ops only
4. Every allow/deny decision emits a signed, hash-chained receipt
5. Standing gates every operation — no implicit local trust path

## Quick Start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
secretctl --help
```

## Project Structure

- `src/custody/` — core library: catalog, policy, standing, adapters, receipts
- `tests/` — unit tests and golden conformance vectors
- `DESIGN.md` — full design document (read this first)

## Conventions

- License: Apache-2.0
- Python 3.10+, type hints everywhere
- Testing: pytest
- Entry point: `python -m custody` / `secretctl`
- Policy and catalog files: YAML
- Enums serialize as stable strings, not integers

## Debugging Discipline

Shared doctrine across the constellation (annotated source: `agent_gov/CLAUDE.md`):

- **Default to reduction.** Escalate to integration only after reduction has failed to discriminate.
- **Belief must be earned by the cheapest available falsification, not constructed by accretion.**

**In this project**, "load-bearing" means any moment a lease is about to be issued, a mediated operation about to execute, or a handle about to be returned to a caller. The cheapest discriminating test is usually: re-verify standing against current policy *right now*, not against the cached attestation from the request. Operation-not-blob is the static version of this rule; the debugging discipline is its dynamic version.

## Don't

- Don't add `get_bytes()` or any raw export path
- Don't store secret material in the catalog
- Don't skip receipt emission for any decision
- Don't make Governor the common path — it's for elevation only
- Don't invent new crypto — compose boring primitives (age, sops, ssh-agent)
