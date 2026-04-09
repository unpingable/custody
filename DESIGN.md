# Custody: Design v0

Custody is not a vault. It is the control surface for sensitive refs: secrets, keys, signing material, and leases.

Its job is simple:

**Who can use which secret how, when, and with what receipt?**

Custody does not own secret storage, identity, or cryptography. It governs *use* of existing material through a ref catalog, standing-gated policy, operation dispatch, and append-only receipts.

## Thesis

Most secret systems try to be everything at once: storage, sync, recovery, identity, policy, and UX. That is how they become annoying, overgrown, and hard to trust.

Custody takes the narrower path:

- **refs, not bytes**
- **use, not export**
- **receipts, not vibes**

The secret material stays in boring existing backends. Custody owns the control plane.

## Non-goals

Custody does **not**:

- store secret bytes as its primary function
- invent new crypto
- replace `ssh-agent`, `age`, `sops`, or a password manager
- own identity or attestation
- own session persistence
- own sync or recovery workflows
- auto-generate or auto-rotate keys in v0
- make raw secret export a normal operation

If you want a vault, this is the wrong repo.

## Scope

Custody **owns**:

- a catalog of secret refs and metadata
- policy evaluation for ref usage
- standing verification integration
- operation dispatch to backend adapters
- lease/usage semantics
- receipt emission and local append-only logging

Custody does **not own**:

- secret material storage
- identity and attestation
- governance decisions outside its scope
- session continuity
- rotation engines

In ecosystem terms:

- **Standing** says who the caller is and what standing they have
- **Governor** mediates elevated or ambiguous requests
- **Continuity** may remember long-lived context around refs, but is not required for use
- **Custody** tracks what a sensitive ref is, how it may be used, and what happened when someone tried

## Design principles

### 1. Refs are handles, not bytes

A ref is a named handle to sensitive material plus metadata and policy. It is never the secret bytes themselves.

### 2. Operations are verbs, not reads

The core abstraction is not `get_secret_bytes()`.

It is:

- `ssh`
- `sign`
- later maybe `decrypt`
- later maybe `mint`

The system should prefer mediated operations over materialization whenever possible.

### 3. Standing gates every operation

Every operation is evaluated against the caller's standing. No standing, no use.

### 4. Governor only for elevation

Straightforward requests should be allowed or denied locally by policy. Governor is for elevated, ambiguous, or break-glass paths, not the common case.

### 5. Receipts are first-class

Every operation attempt emits a receipt: who asked, for what, in what context, under which policy, with what result.

### 6. Boring substrate

Custody should compose existing tools, not replace them.

Initial targets:

- `ssh-agent` for SSH-backed use
- later `age` / `sops` for file-backed decryption or wrapping

## Constraints and invariants

Custody is only useful if its boundaries are mechanically hard to violate. v0 states its invariants explicitly.

### Core invariants

1. **Refs are metadata, never secret bytes**
   - The catalog must not contain raw secret material.
   - Backend selectors may identify material by fingerprint, keygrip, comment, path, or opaque handle only.

2. **Default deny**
   - If standing is missing, invalid, expired, or unverifiable, deny.
   - If no policy rule matches, deny.
   - If backend selector resolution is ambiguous, deny.
   - If a required receipt cannot be written, the operation outcome is suspect and must be surfaced loudly.

3. **Operation-not-blob**
   - v0 supports mediated operations only.
   - Raw export is not a normal operation.
   - `get_bytes()` is not a public abstraction.

4. **Policy binds to canonical refs**
   - Aliases may exist for operator convenience.
   - Authorization evaluates against canonical ref ids only.

5. **Receipts are first-class**
   - Every allow/deny decision emits a receipt.
   - Receipts are append-only, hash-chained, and signed.
   - Receipt verification must not require network access.

6. **Standing gates every operation**
   - No "local implicit trust" path in normal use.
   - Any break-glass path must be explicit and separately receipted.

7. **Backend adapters must minimize exposure**
   - Prefer delegated use over materialization.
   - Adapters should return structured outcomes, not raw secret material.

8. **Governor is for elevation, not the common path**
   - Straightforward allow/deny decisions should be local and deterministic.
   - Governor mediation is opt-in per policy rule.

### v0 constraints

- No secret sync
- No recovery workflow
- No browser/autofill UX
- No key generation
- No automated rotation
- No export operation
- Single-node local receipt log
- One backend adapter required: `ssh-agent`

## Ref model

Canonical ref format:

```text
<class>/<scope>/<name>[@version]
```

Examples:

```text
ssh/prod/deploy
ssh/staging/ops
signing/release/macos
repo/github/ci-bot
```

Properties of a ref:

- stable canonical identifier
- class (`ssh`, `signing`, `repo`, etc.)
- scope/environment
- backend type
- allowed operations
- lease TTL
- owner / rotation owner
- break-glass marker
- provenance / custody metadata

Refs may have human-friendly aliases, but policy binds to canonical refs.

### Ref schema

```yaml
refs:
  - id: ssh/prod/deploy
    backend: ssh-agent
    selector:
      fingerprint: "SHA256:abc123..."
      comment: "deploy@prod"
    class: ssh
    owner: platform
    scope: prod
    allowed_ops: [ssh]
    lease_ttl_seconds: 900
    break_glass: false
    rotation_hint: manual

  - id: ssh/staging/ops
    backend: ssh-agent
    selector:
      fingerprint: "SHA256:def456..."
      comment: "ops@staging"
    class: ssh
    owner: platform
    scope: staging
    allowed_ops: [ssh]
    lease_ttl_seconds: 1800
    break_glass: false
    rotation_hint: manual

  - id: signing/release/macos
    backend: ssh-agent
    selector:
      fingerprint: "SHA256:ghi789..."
      comment: "release-signing"
    class: signing
    owner: release-eng
    scope: release
    allowed_ops: [sign]
    lease_ttl_seconds: 300
    break_glass: false
    rotation_hint: quarterly
```

### Schema constraints

#### Ref id format

Constraints:

- lowercase ASCII
- `/` separates segments
- `@version` optional
- no whitespace
- aliases must resolve to exactly one canonical ref

Regex:

```text
^[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*(?:@[A-Za-z0-9._-]+)?$
```

#### Lease TTL

- integer seconds
- must be > 0
- should be bounded by policy
- v0 default max: 3600 seconds unless explicitly overridden

## Operation model

Supported operations in v0:

- `ssh`

Planned later:

- `sign`
- `decrypt`

Explicitly **not supported** in v0:

- `export`
- `get-bytes`

If export ever exists, it must be:

- explicit
- rare
- separately classed
- break-glass only
- Governor-mediated
- loudly receipted

### Semantics

An operation request is:

```text
(ref, op, caller, target_context) -> decision -> dispatch -> receipt
```

The dispatch layer talks to the real backend. Custody should avoid touching raw secret material unless there is no other choice.

## Policy model

v0 uses a simple declarative policy file. No Rego. No CEL. No policy cathedral.

A policy rule binds:

- ref matcher
- allowed operation(s)
- required standing predicates
- optional target constraints
- lease TTL
- whether Governor mediation is required

### Policy schema

```yaml
rules:
  - id: allow-prod-deploy-ssh
    ref: ssh/prod/deploy
    allow_ops: [ssh]
    require:
      standing:
        role: deployer
        env: prod
      ttl_seconds: 900
    governor: false

  - id: allow-staging-ops-ssh
    ref: ssh/staging/ops
    allow_ops: [ssh]
    require:
      standing:
        role: operator
        env: staging
      ttl_seconds: 1800
    governor: false

  - id: release-signing-elevated
    ref: signing/release/macos
    allow_ops: [sign]
    require:
      standing:
        role: release-engineer
      ttl_seconds: 300
    governor: true
```

### Policy evaluation order

1. resolve ref
2. verify standing
3. match policy
4. deny by default
5. if matched and `governor: true`, request Governor decision
6. dispatch if allowed
7. emit receipt

## Receipts

Every operation attempt emits a receipt, whether allowed or denied.

Receipts must be:

- append-only
- hash-chained
- locally verifiable
- signed by a custody-local signing key
- suitable for later publication or export into broader receipt systems

### Receipt contents

Minimum fields:

- `receipt_id`
- `timestamp`
- `principal`
- `standing_summary`
- `ref_id`
- `operation`
- `target_context`
- `policy_rule_id`
- `governor_mediated`
- `decision` (`allow` / `deny`)
- `reason`
- `lease_ttl_seconds`
- `backend`
- `materialized` (`false` in normal v0 flow)
- `prev_receipt_hash`
- `receipt_hash`
- `signature`

Receipts are about *use*, not secret contents.

### Receipt wire format (frozen)

These choices are frozen for v0. Changes require updating goldens deliberately.

- **Serialization**: canonical JSON — sorted keys, no extra whitespace, UTF-8
- **Hash algorithm**: SHA-256 over the canonical JSON bytes (excluding `receipt_hash` and `signature` fields)
- **Signature algorithm**: Ed25519 over the `receipt_hash` bytes
- **Genesis marker**: SHA-256 of the literal string `custody:genesis:v0`
- **Receipt chain**: every receipt includes `prev_receipt_hash`; chain starts from the genesis marker

### Standing client contract (frozen)

The standing client stub interface for v0:

```python
class StandingSummary:
    principal: str          # who the caller is
    expires_at: datetime    # when this standing expires
    claims: dict[str, str]  # role, env, etc. — matched by policy
    attestation_id: str     # opaque handle for receipt logging

class StandingError:
    code: str               # missing | invalid | expired | unreachable
    message: str

def verify(token: str) -> StandingSummary | StandingError: ...
```

Policy evaluates against `claims`. Receipts log `principal`, `attestation_id`, and `expires_at`. This shape must not diverge between the policy evaluator and receipt schema.

### SSH execution semantics (frozen)

v0 SSH adapter is resolve + authorize + shell out. It does not broker the connection.

1. Resolve ref selector against `ssh-agent` (match by fingerprint/comment)
2. Policy check (standing + policy rule)
3. `subprocess.run(["ssh", "-o", f"IdentityAgent={agent_sock}", "-i", pubkey_path, target])` or equivalent
4. Receipt the attempt and outcome

The adapter is deliberately stupid. No agent multiplexing, no connection pooling, no PTY management.

## Canonical enums

These enums are part of the public model. They should be stable, serialized explicitly, and versioned carefully.

> Rust-like enum notation is used as schema shorthand. The spec is language-agnostic; the v0 implementation is Python.

### RefClass

```rust
enum RefClass {
    Ssh,
    Signing,
    RepoToken,
    DecryptKey,
    Lease,
    Other(String),
}
```

### BackendKind

```rust
enum BackendKind {
    SshAgent,
    Age,
    Sops,
    FileHandle,
    EnvHandle,
    Other(String),
}
```

### OperationKind

```rust
enum OperationKind {
    Ssh,
    Sign,
    Decrypt,
    Mint,
    Export, // reserved; unsupported in v0
}
```

### Decision

```rust
enum Decision {
    Allow,
    Deny,
}
```

### DenyReason

```rust
enum DenyReason {
    MissingStanding,
    InvalidStanding,
    ExpiredStanding,
    RefNotFound,
    AliasUnresolved,
    NoMatchingPolicy,
    OperationNotAllowed,
    GovernorRequired,
    GovernorDenied,
    BackendUnavailable,
    SelectorMismatch,
    AmbiguousSelector,
    ReceiptFailure,
    BreakGlassRequired,
    UnsupportedOperation,
}
```

### MediationMode

```rust
enum MediationMode {
    LocalPolicyOnly,
    GovernorRequired,
}
```

### MaterializationMode

```rust
enum MaterializationMode {
    IndirectUse,   // normal path
    Materialized,  // reserved for future break-glass/export paths
}
```

### BreakGlassMode

```rust
enum BreakGlassMode {
    None,
    Explicit,
}
```

### ReceiptOutcome

```rust
enum ReceiptOutcome {
    Allowed,
    Denied,
    AllowedButReceiptSuspect,
}
```

### SelectorKind

```rust
enum SelectorKind {
    Fingerprint,
    Comment,
    Keygrip,
    Path,
    OpaqueHandle,
}
```

## Backend adapters

Backend adapters provide operation-specific dispatch without turning Custody into a vault.

v0 adapter:

- `ssh-agent`

Future adapters:

- `age`
- `sops`
- signing backend(s)

Adapter contract:

- confirm selector resolves to expected material
- perform the requested operation
- return structured outcome
- never expose more material than necessary

## First slice: SSH

The first slice is governed SSH use via existing `ssh-agent`.

CLI:

```bash
secretctl use ssh/prod/deploy --op ssh --target host.example.com
```

Flow:

1. load catalog
2. resolve `ssh/prod/deploy`
3. verify caller standing
4. evaluate local policy
5. optionally ask Governor
6. resolve SSH key identity in `ssh-agent`
7. dispatch SSH operation
8. emit receipt

Important constraint: Custody identifies keys by public selector data such as fingerprint/comment. It does not store private key material.

## CLI sketch

```bash
secretctl list
secretctl show ssh/prod/deploy
secretctl explain ssh/prod/deploy
secretctl use ssh/prod/deploy --op ssh --target host.example.com
secretctl receipts tail
secretctl receipts verify
```

### Command intent

- `list`: available refs
- `show`: ref metadata
- `explain`: why this caller can or cannot use the ref
- `use`: execute a governed operation
- `receipts`: inspect and verify the append-only trail

## Failure model

Custody should fail closed.

Examples:

- no standing -> deny
- ref not found -> deny
- policy match absent -> deny
- backend selector mismatch -> deny
- Governor unavailable for required elevated path -> deny
- receipt emission failure after attempted operation -> mark operation outcome as suspect and surface loudly

No silent fallback to raw secret access.

## Golden tests and conformance vectors

Custody needs more than unit tests. It needs stable artifacts that prove the model has not drifted.

### 1. Catalog parse goldens

Input:
- valid `catalog.yaml`
- invalid variants: duplicate ids, alias collisions, illegal ref ids, raw-byte contamination

Assert:
- parsed model matches expected canonical JSON
- invalid inputs fail with stable error classes

### 2. Policy evaluation goldens

Given:
- catalog
- standing token summary
- operation request

Assert:
- exact decision
- matched policy rule id
- deny reason if denied
- whether Governor mediation is required

These should be table-driven fixtures.

### 3. Receipt serialization goldens

For a fixed input decision, assert:
- canonical serialized form
- receipt hash
- signature verification result
- `prev_receipt_hash` chaining

If receipt bytes drift unintentionally, the test must scream.

### 4. Receipt chain vectors

Ship a tiny vector set:

- genesis -> receipt A
- receipt A -> receipt B
- tampered receipt B
- wrong previous hash
- wrong signature

Assert verifier behavior for each.

### 5. CLI explain goldens

For `secretctl explain <ref>` and denial cases, snapshot the structured explanation output.

### 6. Adapter dry-run goldens

For the SSH adapter, use a fake adapter or fixture-backed mode to assert:

- selector resolution success
- selector ambiguity
- selector mismatch
- backend unavailable

Core conformance must not depend on a live agent.

### 7. Unsupported operation tests

Explicitly assert that `Export` is rejected in v0 with a stable error class and stable explanation.

### 8. Alias resolution tests

Assert:
- alias -> canonical ref resolution
- policy always evaluates canonical ref
- alias ambiguity is a hard failure

## Compatibility contract

The following surfaces are compatibility-sensitive in v0:

- serialized receipt schema
- receipt hashing/signing behavior
- canonical ref id syntax
- public enum values
- deny reason codes
- policy rule matching semantics

If any of these change, update schema/version markers and regenerate goldens deliberately.

## Repository layout

```text
custody/
  DESIGN.md
  pyproject.toml
  src/custody/
    __init__.py
    catalog/
      schema.py
      loader.py
    policy/
      schema.py
      eval.py
    standing/
      client.py
    adapters/
      __init__.py
      ssh_agent.py
    receipts/
      schema.py
      signer.py
      log.py
    cli/
      secretctl.py
  tests/
    conftest.py
    goldens/
```

## v0 milestones

### Milestone 1: skeleton

- catalog schema
- policy schema
- standing client stub
- receipt schema
- CLI skeleton

### Milestone 2: local decision path

- load refs
- evaluate policy
- deny by default
- emit receipts for allow/deny

### Milestone 3: SSH adapter

- resolve selector against `ssh-agent`
- perform governed SSH use
- receipt logging end-to-end

### Milestone 4: Governor integration

- elevated requests
- explicit mediation path
- mediation outcome in receipts

## Future work

- sign adapter
- decrypt adapter
- break-glass export semantics
- rotation metadata
- continuity integration
- richer policy predicates
