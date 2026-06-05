"""Builds the per-user context every personal agent reasons over."""

from __future__ import annotations


def build_context(kb: dict) -> dict:
    profile = kb.get("profile", {})
    sc = kb.get("scorecard", {})
    systems = {s["system"]: s for s in kb.get("systems", [])}
    coupling = kb.get("coupling", [])
    worst = max(coupling, key=lambda c: abs(c.get("delta_vs_baseline") or 0), default=None)
    metrics = {it.get("label"): it for it in kb.get("knowledge_base", [])}
    events = kb.get("day", {}).get("events", [])
    by_type = lambda t: [e for e in events if e.get("type") == t]  # noqa: E731

    return {
        "name": profile.get("display_name", "there"),
        "bio_age": sc.get("biological_age"),
        "chron_age": sc.get("chronological_age"),
        "age_accel": sc.get("age_accel"),
        "delta": sc.get("delta_vs_baseline"),
        "systems": systems,
        "watch": [k for k, v in systems.items() if v.get("status") == "watch"],
        "coupling": coupling,
        "worst": worst,
        "metrics": metrics,
        "meals": by_type("meal"),
        "exercise": by_type("exercise"),
        "supplements": by_type("supplement"),
        "light": by_type("light"),
        "interventions": [
            {"id": i.get("id"), "title": i.get("title"), "status": i.get("status")}
            for i in kb.get("interventions", [])
        ],
    }


def coupling_line(ctx: dict) -> str:
    w = ctx.get("worst")
    if not w:
        return "your overnight coupling is the metric to watch"
    return (
        f"your {w.get('label', 'coupling').lower()} is down "
        f"{abs(w.get('delta_vs_baseline') or 0):.2f} vs your baseline"
    )


def metric_value(ctx: dict, label: str, default: str) -> str:
    item = ctx.get("metrics", {}).get(label)
    return item.get("value", default) if item else default


def named_food(q: str):
    for w in ("rice", "bread", "pasta", "pizza", "dessert", "sugar", "fruit", "ice cream",
              "cake", "soda", "juice", "chocolate", "burger", "fries"):
        if w in q:
            return w
    return None
