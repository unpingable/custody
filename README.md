# custody

Chain-of-custody control surface for sensitive refs: secrets, keys, signing material, and leases.

## What it does

- Governs *use* of existing secret material through standing-gated policy
- Dispatches mediated operations (ssh, sign) to backend adapters
- Emits signed, hash-chained receipts for every allow/deny decision

## What this is not

- Not a vault — does not store secret bytes
- Not an identity system — that's [Standing](https://github.com/unpingable/standing)
- Not a governance engine — that's [Governor](https://github.com/unpingable/governor)

## Invariants

Custody is only useful if its boundaries hold.

1. Refs are metadata handles, never the bytes themselves
2. Default deny — no standing, no policy match, no access
3. Operations are verbs (ssh, sign), not reads (get_bytes)
4. Every decision emits a signed receipt

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
secretctl --help
```

## Architecture

See [DESIGN.md](DESIGN.md) for the full design document.

## License

Licensed under Apache-2.0.
