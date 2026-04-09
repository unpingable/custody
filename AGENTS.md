# AGENTS.md — Working in this repo

This file is a **travel guide**, not a law.
If anything here conflicts with the user's explicit instructions, the user wins.

> Instruction files shape behavior; the user determines direction.

---

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Tests

```bash
source .venv/bin/activate
pytest
```

Always run tests before proposing commits. Never claim tests pass without running them.

---

## Safety and irreversibility

### Do not do these without explicit user confirmation
- Push to remote, create/close PRs or issues
- Delete or rewrite git history
- Modify dependency files in ways that change the lock file
- Add any form of `get_bytes()` or raw export path

### Preferred workflow
- Make changes in small, reviewable steps
- Run tests locally before proposing commits
- For any operation that affects external state, require explicit user confirmation

---

## Repository layout

```
custody/
  DESIGN.md          — full design document (read first)
  src/custody/
    catalog/         — ref catalog schema and loading
    policy/          — declarative policy schema and evaluation
    standing/        — standing verification client
    adapters/        — backend adapters (ssh-agent, etc.)
    receipts/        — receipt schema, signing, append-only log
    cli/             — secretctl CLI
  tests/             — pytest tests and golden vectors
```

---

## Coding conventions

- Python 3.10+, type hints on all public interfaces
- pytest for testing, golden vectors for conformance
- YAML for catalog and policy files
- Enums serialize as stable lowercase strings

---

## Invariants

These are non-negotiable. If these break, something is wrong.

1. Refs are metadata handles, never secret bytes
2. Default deny on missing standing, no policy match, or ambiguous selectors
3. Every decision (allow or deny) emits a signed, hash-chained receipt
4. `get_bytes()` / raw export does not exist in v0
5. Standing gates every operation — no implicit trust path

---

## What this is not

- Not a vault — Custody never stores or owns secret bytes
- Not an identity system — Standing handles identity/attestation
- Not a governance engine — Governor handles elevated decisions
- Not a key manager — v0 does not generate or rotate keys

---

## When you're unsure

Ask for clarification rather than guessing, especially around:
- Whether a change introduces materialization of secret bytes
- Receipt schema changes (compatibility-sensitive surface)
- Policy evaluation semantics changes
- Anything that changes a documented invariant

---

## Agent-specific instruction files

| Agent | File | Role |
|-------|------|------|
| Claude Code | `CLAUDE.md` | Full operational context, build details, conventions |
| Codex | `AGENTS.md` (this file) | Operating context + defaults |
| Any future agent | `AGENTS.md` (this file) | Start here |
