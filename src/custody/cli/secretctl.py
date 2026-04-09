"""secretctl — CLI for Custody.

Commands:
  list       — available refs
  show       — ref metadata
  explain    — why this caller can or cannot use the ref
  use        — execute a governed operation
  receipts   — inspect and verify the append-only trail
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from custody.catalog.loader import load_catalog
from custody.enums import Decision, DenyReason, OperationKind
from custody.policy.loader import load_policy
from custody.policy.eval import DecisionResult, evaluate
from custody.standing.client import StandingError, StandingSummary


def cmd_list(args: argparse.Namespace) -> None:
    catalog = load_catalog(Path(args.catalog))
    for ref_id, ref in sorted(catalog.refs.items()):
        ops = ", ".join(op.value for op in ref.allowed_ops)
        print(f"{ref_id}  [{ref.ref_class.value}]  ops=[{ops}]  backend={ref.backend.value}")


def cmd_show(args: argparse.Namespace) -> None:
    catalog = load_catalog(Path(args.catalog))
    ref = catalog.resolve(args.ref)
    if ref is None:
        print(f"ref not found: {args.ref}", file=sys.stderr)
        sys.exit(1)
    info = {
        "id": ref.id,
        "class": ref.ref_class.value,
        "backend": ref.backend.value,
        "scope": ref.scope,
        "owner": ref.owner,
        "allowed_ops": [op.value for op in ref.allowed_ops],
        "lease_ttl_seconds": ref.lease_ttl_seconds,
        "break_glass": ref.break_glass,
        "selectors": [{"kind": s.kind.value, "value": s.value} for s in ref.selectors],
    }
    print(json.dumps(info, indent=2))


def cmd_explain(args: argparse.Namespace) -> None:
    catalog = load_catalog(Path(args.catalog))
    policy = load_policy(Path(args.policy))

    # In v0, standing comes from a token (stub: always fails unless overridden)
    from custody.standing.client import verify
    standing = verify(args.standing_token or "")

    op = OperationKind(args.op)
    result = evaluate(catalog, policy, standing, args.ref, op)

    explanation = {
        "ref": result.ref_id,
        "operation": result.operation.value,
        "decision": result.decision.value,
    }
    if result.deny_reason:
        explanation["deny_reason"] = result.deny_reason.value
    if result.matched_rule:
        explanation["matched_rule"] = result.matched_rule.id
    explanation["mediation"] = result.mediation.value

    print(json.dumps(explanation, indent=2))
    if result.decision == Decision.DENY:
        sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="secretctl", description="Custody CLI")
    parser.add_argument("--catalog", default="catalog.yaml", help="Path to catalog file")
    parser.add_argument("--policy", default="policy.yaml", help="Path to policy file")
    parser.add_argument("--standing-token", default="", help="Standing token")

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="List available refs")

    show_p = sub.add_parser("show", help="Show ref metadata")
    show_p.add_argument("ref", help="Ref id or alias")

    explain_p = sub.add_parser("explain", help="Explain access decision")
    explain_p.add_argument("ref", help="Ref id or alias")
    explain_p.add_argument("--op", required=True, help="Operation kind")

    use_p = sub.add_parser("use", help="Execute a governed operation")
    use_p.add_argument("ref", help="Ref id or alias")
    use_p.add_argument("--op", required=True, help="Operation kind")
    use_p.add_argument("--target", required=True, help="Target context")

    receipts_p = sub.add_parser("receipts", help="Receipt operations")
    receipts_sub = receipts_p.add_subparsers(dest="receipts_command")
    receipts_sub.add_parser("tail", help="Show recent receipts")
    receipts_sub.add_parser("verify", help="Verify receipt chain")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "list":
        cmd_list(args)
    elif args.command == "show":
        cmd_show(args)
    elif args.command == "explain":
        cmd_explain(args)
    elif args.command == "use":
        print("use: not yet implemented", file=sys.stderr)
        sys.exit(1)
    elif args.command == "receipts":
        print("receipts: not yet implemented", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
