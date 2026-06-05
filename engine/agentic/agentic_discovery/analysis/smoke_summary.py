"""Minimal approved analysis used to test guarded Slurm execution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agentic_discovery.store import AgenticDiscoveryStore


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    store = AgenticDiscoveryStore(args.state_root)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "metrics": {
            "candidate_count": len(store.candidates.all()),
            "method_plan_count": len(store.method_plans.all()),
            "verification_count": len(store.verifications.all()),
        },
        "status": "completed",
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
