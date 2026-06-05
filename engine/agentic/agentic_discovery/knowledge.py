"""CLI for literature, tool, dataset, and claim registries."""

from __future__ import annotations

import argparse
import json

from .retrieval import build_index, search
from .schemas import (
    DatasetRecord,
    ExtractedClaim,
    PaperRecord,
    SurpriseRecord,
    ToolRecord,
    record_to_dict,
)
from .store import AgenticDiscoveryStore


COLLECTIONS = ["papers", "claims", "tools", "datasets", "surprises"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", default=None, help="Override registry state directory.")
    sub = parser.add_subparsers(dest="command", required=True)

    paper = sub.add_parser("add-paper", help="Register a paper.")
    paper.add_argument("--title", required=True)
    paper.add_argument("--author", action="append", default=[], dest="authors")
    paper.add_argument("--year", type=int)
    paper.add_argument("--venue", default="")
    paper.add_argument("--doi", default="")
    paper.add_argument("--url", default="")
    paper.add_argument("--abstract", default="")
    paper.add_argument("--topic", action="append", default=[], dest="topics")
    paper.add_argument("--modality", action="append", default=[], dest="modalities")
    paper.add_argument("--aging-relevance", default="")
    paper.add_argument("--disease-relevance", default="")
    paper.add_argument("--evidence-level", default="")
    paper.add_argument("--source", default="")
    paper.add_argument("--tag", action="append", default=[], dest="tags")
    paper.add_argument("--notes", default="")
    paper.add_argument("--dry-run", action="store_true")

    claim = sub.add_parser("add-claim", help="Register an extracted claim from a paper or source.")
    claim.add_argument("--statement", required=True)
    claim.add_argument("--paper-id", default="")
    claim.add_argument("--direction", default="")
    claim.add_argument("--population", default="")
    claim.add_argument("--modality", default="")
    claim.add_argument("--outcome", default="")
    claim.add_argument("--mechanism", default="")
    claim.add_argument("--method", action="append", default=[], dest="methods")
    claim.add_argument("--caveat", action="append", default=[], dest="caveats")
    claim.add_argument("--supports", action="append", default=[], dest="supports_hypotheses")
    claim.add_argument("--contradicts", action="append", default=[], dest="contradicts_hypotheses")
    claim.add_argument("--tag", action="append", default=[], dest="tags")
    claim.add_argument("--dry-run", action="store_true")

    tool = sub.add_parser("add-tool", help="Register a tool or method.")
    tool.add_argument("--name", required=True)
    tool.add_argument("--version", default="")
    tool.add_argument("--source-url", default="")
    tool.add_argument("--purpose", required=True)
    tool.add_argument("--task-type", action="append", default=[], dest="task_types")
    tool.add_argument("--modality", action="append", default=[], dest="modalities")
    tool.add_argument("--input", action="append", default=[], dest="inputs")
    tool.add_argument("--output", action="append", default=[], dest="outputs")
    tool.add_argument("--install-notes", default="")
    tool.add_argument("--validation-notes", default="")
    tool.add_argument("--limitation", action="append", default=[], dest="limitations")
    tool.add_argument("--license", default="")
    tool.add_argument("--tag", action="append", default=[], dest="tags")
    tool.add_argument("--dry-run", action="store_true")

    dataset = sub.add_parser("add-dataset", help="Register a relevant dataset.")
    dataset.add_argument("--name", required=True)
    dataset.add_argument("--source-url", default="")
    dataset.add_argument("--population", default="")
    dataset.add_argument("--modality", action="append", default=[], dest="modalities")
    dataset.add_argument("--outcome", action="append", default=[], dest="outcomes")
    dataset.add_argument("--access-status", default="")
    dataset.add_argument("--sample-size", type=int)
    dataset.add_argument("--age-range", default="")
    dataset.add_argument("--disease-group", action="append", default=[], dest="disease_groups")
    dataset.add_argument("--time-resolution", default="")
    dataset.add_argument("--strength", action="append", default=[], dest="strengths")
    dataset.add_argument("--limitation", action="append", default=[], dest="limitations")
    dataset.add_argument("--leakage-risk", action="append", default=[], dest="leakage_risks")
    dataset.add_argument("--external-validation-use", action="append", default=[], dest="external_validation_uses")
    dataset.add_argument("--tag", action="append", default=[], dest="tags")
    dataset.add_argument("--notes", default="")
    dataset.add_argument("--dry-run", action="store_true")

    surprise = sub.add_parser("add-surprise", help="Register an unexpected data or analysis finding.")
    surprise.add_argument("--summary", required=True)
    surprise.add_argument("--origin-artifact", default="")
    surprise.add_argument("--details", default="")
    surprise.add_argument("--modality", default="")
    surprise.add_argument("--signal", default="")
    surprise.add_argument("--candidate-id", action="append", default=[], dest="candidate_ids")
    surprise.add_argument("--hypothesis-id", action="append", default=[], dest="hypothesis_ids")
    surprise.add_argument("--severity", default="medium")
    surprise.add_argument("--p-hacking-risk", default="")
    surprise.add_argument("--follow-up-needed", action="append", default=[], dest="follow_up_needed")
    surprise.add_argument("--tag", action="append", default=[], dest="tags")
    surprise.add_argument("--dry-run", action="store_true")

    list_cmd = sub.add_parser("list", help="List registry records.")
    list_cmd.add_argument("collection", choices=COLLECTIONS)
    list_cmd.add_argument("--limit", type=int, default=25)
    list_cmd.add_argument("--json", action="store_true")

    index = sub.add_parser("index", help="Build retrieval index.")
    index.add_argument("--no-legacy", action="store_true")

    search_cmd = sub.add_parser("search", help="Search registries and legacy hypotheses.")
    search_cmd.add_argument("query")
    search_cmd.add_argument("--kind", action="append", default=[])
    search_cmd.add_argument("--limit", type=int, default=10)
    search_cmd.add_argument("--json", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = AgenticDiscoveryStore(args.state_root)

    if args.command == "add-paper":
        record = PaperRecord(
            title=args.title,
            authors=args.authors,
            year=args.year,
            venue=args.venue,
            doi=args.doi,
            url=args.url,
            abstract=args.abstract,
            topics=args.topics,
            modalities=args.modalities,
            aging_relevance=args.aging_relevance,
            disease_relevance=args.disease_relevance,
            evidence_level=args.evidence_level,
            source=args.source,
            tags=args.tags,
            notes=args.notes,
        )
        return _append_or_print(store, store.papers, record, args.dry_run)

    if args.command == "add-claim":
        record = ExtractedClaim(
            statement=args.statement,
            paper_id=args.paper_id,
            direction=args.direction,
            population=args.population,
            modality=args.modality,
            outcome=args.outcome,
            mechanism=args.mechanism,
            methods=args.methods,
            caveats=args.caveats,
            supports_hypotheses=args.supports_hypotheses,
            contradicts_hypotheses=args.contradicts_hypotheses,
            tags=args.tags,
        )
        return _append_or_print(store, store.claims, record, args.dry_run)

    if args.command == "add-tool":
        record = ToolRecord(
            name=args.name,
            version=args.version,
            source_url=args.source_url,
            purpose=args.purpose,
            task_types=args.task_types,
            modalities=args.modalities,
            inputs=args.inputs,
            outputs=args.outputs,
            install_notes=args.install_notes,
            validation_notes=args.validation_notes,
            limitations=args.limitations,
            license=args.license,
            tags=args.tags,
        )
        return _append_or_print(store, store.tools, record, args.dry_run)

    if args.command == "add-dataset":
        record = DatasetRecord(
            name=args.name,
            source_url=args.source_url,
            population=args.population,
            modalities=args.modalities,
            outcomes=args.outcomes,
            access_status=args.access_status,
            sample_size=args.sample_size,
            age_range=args.age_range,
            disease_groups=args.disease_groups,
            time_resolution=args.time_resolution,
            strengths=args.strengths,
            limitations=args.limitations,
            leakage_risks=args.leakage_risks,
            external_validation_uses=args.external_validation_uses,
            tags=args.tags,
            notes=args.notes,
        )
        return _append_or_print(store, store.datasets, record, args.dry_run)

    if args.command == "add-surprise":
        record = SurpriseRecord(
            summary=args.summary,
            origin_artifact=args.origin_artifact,
            details=args.details,
            modality=args.modality,
            signal=args.signal,
            candidate_ids=args.candidate_ids,
            hypothesis_ids=args.hypothesis_ids,
            severity=args.severity,
            p_hacking_risk=args.p_hacking_risk,
            follow_up_needed=args.follow_up_needed,
            tags=args.tags,
        )
        return _append_or_print(store, store.surprises, record, args.dry_run)

    if args.command == "list":
        records = store.collection(args.collection).all()[: args.limit]
        if args.json:
            print(json.dumps([record_to_dict(record) for record in records], indent=2, sort_keys=True))
            return 0
        for record in records:
            data = record_to_dict(record)
            record_id = next((value for key, value in data.items() if key.endswith("_id")), "")
            title = data.get("title") or data.get("name") or data.get("statement") or data.get("summary") or ""
            print(f"{record_id}\t{title}")
        return 0

    if args.command == "index":
        result = build_index(store, include_legacy=not args.no_legacy)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "search":
        hits = search(args.query, store=store, kinds=args.kind or None, limit=args.limit)
        if args.json:
            print(json.dumps(hits, indent=2, sort_keys=True))
            return 0
        for hit in hits:
            print(f"{hit['doc_id']}\t[{hit['kind']}]\t{hit['title']}")
            if hit["snippet"]:
                print(f"  {hit['snippet']}")
        return 0

    raise AssertionError(args.command)


def _append_or_print(store: AgenticDiscoveryStore, collection, record, dry_run: bool) -> int:
    if dry_run:
        print(json.dumps(record_to_dict(record), indent=2, sort_keys=True))
        return 0
    record = collection.append(record)
    build_index(store)
    print(f"registered {getattr(record, collection.id_field)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
