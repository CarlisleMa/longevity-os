"""CLI for hypothesis graph edges."""

from __future__ import annotations

import argparse
import json

from .retrieval import build_index
from .schemas import EDGE_TYPES, HypothesisEdge, record_to_dict
from .store import AgenticDiscoveryStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", default=None, help="Override registry state directory.")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add-edge", help="Add a relationship between hypotheses, candidates, or evidence.")
    add.add_argument("--source", required=True, dest="source_id")
    add.add_argument("--target", required=True, dest="target_id")
    add.add_argument("--type", required=True, choices=EDGE_TYPES, dest="edge_type")
    add.add_argument("--rationale", default="")
    add.add_argument("--evidence-id", action="append", default=[], dest="evidence_ids")
    add.add_argument("--confidence", type=float, default=0.5)
    add.add_argument("--created-by", default="human")
    add.add_argument("--dry-run", action="store_true")

    list_cmd = sub.add_parser("list", help="List graph edges.")
    list_cmd.add_argument("--source")
    list_cmd.add_argument("--target")
    list_cmd.add_argument("--type", choices=EDGE_TYPES, dest="edge_type")
    list_cmd.add_argument("--json", action="store_true")

    related = sub.add_parser("related", help="List edges touching a node.")
    related.add_argument("node_id")
    related.add_argument("--json", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = AgenticDiscoveryStore(args.state_root)

    if args.command == "add-edge":
        edge = HypothesisEdge(
            source_id=args.source_id,
            target_id=args.target_id,
            edge_type=args.edge_type,
            rationale=args.rationale,
            evidence_ids=args.evidence_ids,
            confidence=args.confidence,
            created_by=args.created_by,
        )
        if args.dry_run:
            print(json.dumps(record_to_dict(edge), indent=2, sort_keys=True))
            return 0
        edge = store.edges.append(edge)
        build_index(store)
        print(f"added {edge.edge_id}: {edge.source_id} {edge.edge_type} {edge.target_id}")
        return 0

    if args.command == "list":
        edges = store.edges.all()
        if args.source:
            edges = [edge for edge in edges if edge.source_id == args.source]
        if args.target:
            edges = [edge for edge in edges if edge.target_id == args.target]
        if args.edge_type:
            edges = [edge for edge in edges if edge.edge_type == args.edge_type]
        return _print_edges(edges, json_output=args.json)

    if args.command == "related":
        edges = [
            edge
            for edge in store.edges.all()
            if edge.source_id == args.node_id or edge.target_id == args.node_id
        ]
        return _print_edges(edges, json_output=args.json)

    raise AssertionError(args.command)


def _print_edges(edges: list[HypothesisEdge], json_output: bool) -> int:
    if json_output:
        print(json.dumps([record_to_dict(edge) for edge in edges], indent=2, sort_keys=True))
        return 0
    for edge in edges:
        print(f"{edge.edge_id}\t{edge.source_id}\t{edge.edge_type}\t{edge.target_id}\tC={edge.confidence:.2f}")
        if edge.rationale:
            print(f"  {edge.rationale}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
