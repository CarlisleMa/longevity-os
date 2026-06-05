"""Retrieval-first context over discovery registries and legacy hypotheses."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .schemas import record_to_dict
from .store import AgenticDiscoveryStore


REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_HYPOTHESES_ROOT = REPO_ROOT / "hypothesis_driven" / "hypotheses"


@dataclass
class Document:
    doc_id: str
    kind: str
    title: str
    body: str
    source_path: str
    payload: dict[str, Any]


def _textify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return " ".join(_textify(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_textify(item) for item in value.values())
    return str(value)


def _document_from_record(kind: str, record: Any, source_path: Path, id_field: str, title_field: str) -> Document:
    payload = record_to_dict(record)
    title = str(payload.get(title_field) or payload.get("name") or payload.get(id_field) or "")
    if hasattr(record, "search_text"):
        body = record.search_text()
    else:
        body = _textify(payload)
    return Document(
        doc_id=str(payload[id_field]),
        kind=kind,
        title=title,
        body=body,
        source_path=str(source_path),
        payload=payload,
    )


def iter_registry_documents(store: AgenticDiscoveryStore) -> Iterable[Document]:
    specs = [
        ("candidate", store.candidates, "candidate_id", "title"),
        ("paper", store.papers, "paper_id", "title"),
        ("claim", store.claims, "claim_id", "statement"),
        ("tool", store.tools, "tool_id", "name"),
        ("dataset", store.datasets, "dataset_id", "name"),
        ("surprise", store.surprises, "surprise_id", "summary"),
        ("method_plan", store.method_plans, "plan_id", "target_id"),
        ("run", store.runs, "run_id", "hypothesis_id"),
        ("verification", store.verifications, "verification_id", "target_id"),
    ]
    for kind, collection, id_field, title_field in specs:
        for record in collection.all():
            yield _document_from_record(kind, record, collection.path, id_field, title_field)


def iter_legacy_hypothesis_documents(root: Path = LEGACY_HYPOTHESES_ROOT) -> Iterable[Document]:
    if not root.exists():
        return
    for path in sorted(root.glob("*.json")):
        if path.name.startswith("proposed_batch"):
            continue
        try:
            payload = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        doc_id = str(payload.get("id") or path.stem)
        title = str(payload.get("title") or doc_id)
        body = " ".join(
            [
                title,
                _textify(payload.get("statement")),
                _textify(payload.get("mechanism")),
                _textify(payload.get("predictions")),
                _textify(payload.get("literature")),
                _textify(payload.get("feasibility")),
                _textify(payload.get("test_plan")),
                _textify(payload.get("results")),
                _textify(payload.get("critic_verdict")),
                _textify(payload.get("notes")),
            ]
        )
        yield Document(
            doc_id=doc_id,
            kind="legacy_hypothesis",
            title=title,
            body=body,
            source_path=str(path),
            payload=payload,
        )


def iter_documents(store: AgenticDiscoveryStore, include_legacy: bool = True) -> Iterable[Document]:
    yield from iter_registry_documents(store)
    if include_legacy:
        yield from iter_legacy_hypothesis_documents()


def build_index(store: AgenticDiscoveryStore, include_legacy: bool = True) -> dict[str, Any]:
    """Build a SQLite retrieval index.

    FTS5 is used when available. A normal ``docs`` table is always written so
    callers can fall back to Python token scoring on systems without FTS5.
    """

    documents = list(iter_documents(store, include_legacy=include_legacy))
    conn = sqlite3.connect(store.index_path())
    try:
        conn.execute("DROP TABLE IF EXISTS docs_fts")
        conn.execute("DROP TABLE IF EXISTS docs")
        conn.execute(
            """
            CREATE TABLE docs (
                doc_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                source_path TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        fts_available = True
        try:
            conn.execute(
                "CREATE VIRTUAL TABLE docs_fts USING fts5(doc_id UNINDEXED, kind UNINDEXED, title, body)"
            )
        except sqlite3.OperationalError:
            fts_available = False
        for doc in documents:
            conn.execute(
                """
                INSERT OR REPLACE INTO docs
                (doc_id, kind, title, body, source_path, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    doc.doc_id,
                    doc.kind,
                    doc.title,
                    doc.body,
                    doc.source_path,
                    json.dumps(doc.payload, sort_keys=True),
                ),
            )
            if fts_available:
                conn.execute(
                    "INSERT INTO docs_fts (doc_id, kind, title, body) VALUES (?, ?, ?, ?)",
                    (doc.doc_id, doc.kind, doc.title, doc.body),
                )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_docs_kind ON docs(kind)"
        )
        conn.commit()
    finally:
        conn.close()
    return {"index_path": str(store.index_path()), "documents": len(documents)}


def search(
    query: str,
    store: AgenticDiscoveryStore | None = None,
    kinds: list[str] | None = None,
    limit: int = 10,
    include_legacy: bool = True,
) -> list[dict[str, Any]]:
    store = store or AgenticDiscoveryStore()
    if not store.index_path().exists():
        build_index(store, include_legacy=include_legacy)
    try:
        return _search_sqlite(query, store, kinds=kinds, limit=limit)
    except sqlite3.Error:
        return _search_python(query, store, kinds=kinds, limit=limit, include_legacy=include_legacy)


def related_hypotheses(
    text: str,
    store: AgenticDiscoveryStore | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    return search(text, store=store, kinds=["candidate", "legacy_hypothesis"], limit=limit)


def retrieve_context_for_candidate(
    candidate_id: str,
    store: AgenticDiscoveryStore | None = None,
    limit: int = 12,
) -> dict[str, Any]:
    store = store or AgenticDiscoveryStore()
    candidate = store.candidates.get(candidate_id)
    if candidate is None:
        raise KeyError(f"Candidate not found: {candidate_id}")
    query = candidate.search_text()
    hits = [hit for hit in search(query, store=store, limit=limit + 1) if hit["doc_id"] != candidate_id]
    return {"candidate": record_to_dict(candidate), "query": query, "hits": hits[:limit]}


def retrieve_context_for_hypothesis(
    hypothesis_id: str,
    store: AgenticDiscoveryStore | None = None,
    limit: int = 12,
) -> dict[str, Any]:
    store = store or AgenticDiscoveryStore()
    target = None
    for doc in iter_legacy_hypothesis_documents():
        if doc.doc_id == hypothesis_id:
            target = doc
            break
    if target is None:
        candidate = store.candidates.get(hypothesis_id)
        if candidate is None:
            raise KeyError(f"Hypothesis or candidate not found: {hypothesis_id}")
        query = candidate.search_text()
        payload = record_to_dict(candidate)
    else:
        query = f"{target.title} {target.body}"
        payload = target.payload
    hits = [hit for hit in search(query, store=store, limit=limit + 1) if hit["doc_id"] != hypothesis_id]
    return {"target": payload, "query": query, "hits": hits[:limit]}


def _search_sqlite(
    query: str,
    store: AgenticDiscoveryStore,
    kinds: list[str] | None,
    limit: int,
) -> list[dict[str, Any]]:
    conn = sqlite3.connect(store.index_path())
    conn.row_factory = sqlite3.Row
    try:
        if _table_exists(conn, "docs_fts") and _tokens(query):
            rows = _search_fts(conn, query, kinds=kinds, limit=limit)
            if rows:
                return rows
        return _search_docs_table(conn, query, kinds=kinds, limit=limit)
    finally:
        conn.close()


def _search_fts(
    conn: sqlite3.Connection,
    query: str,
    kinds: list[str] | None,
    limit: int,
) -> list[dict[str, Any]]:
    fts_query = " OR ".join(token + "*" for token in _tokens(query)[:16])
    params: list[Any] = [fts_query]
    where = "docs_fts MATCH ?"
    if kinds:
        placeholders = ",".join("?" for _ in kinds)
        where += f" AND kind IN ({placeholders})"
        params.extend(kinds)
    params.append(limit)
    rows = conn.execute(
        f"""
        SELECT d.doc_id, d.kind, d.title, d.body, d.source_path, d.payload_json,
               bm25(docs_fts) AS score
        FROM docs_fts
        JOIN docs d ON docs_fts.doc_id = d.doc_id
        WHERE {where}
        ORDER BY score
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [_row_to_hit(row) for row in rows]


def _search_docs_table(
    conn: sqlite3.Connection,
    query: str,
    kinds: list[str] | None,
    limit: int,
) -> list[dict[str, Any]]:
    params: list[Any] = []
    where = "1 = 1"
    if kinds:
        placeholders = ",".join("?" for _ in kinds)
        where += f" AND kind IN ({placeholders})"
        params.extend(kinds)
    rows = conn.execute(
        f"SELECT doc_id, kind, title, body, source_path, payload_json FROM docs WHERE {where}"
    ).fetchall()
    scored = []
    tokens = _tokens(query)
    for row in rows:
        score = _token_score(tokens, f"{row['title']} {row['body']}")
        if score > 0:
            scored.append((score, _row_to_hit(row, score=-score)))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [hit for _, hit in scored[:limit]]


def _search_python(
    query: str,
    store: AgenticDiscoveryStore,
    kinds: list[str] | None,
    limit: int,
    include_legacy: bool,
) -> list[dict[str, Any]]:
    tokens = _tokens(query)
    scored = []
    for doc in iter_documents(store, include_legacy=include_legacy):
        if kinds and doc.kind not in kinds:
            continue
        score = _token_score(tokens, f"{doc.title} {doc.body}")
        if score > 0:
            scored.append(
                (
                    score,
                    {
                        "doc_id": doc.doc_id,
                        "kind": doc.kind,
                        "title": doc.title,
                        "source_path": doc.source_path,
                        "score": -float(score),
                        "snippet": _snippet(doc.body, tokens),
                        "payload": doc.payload,
                    },
                )
            )
    scored.sort(key=lambda item: item[0], reverse=True)
    return [hit for _, hit in scored[:limit]]


def _row_to_hit(row: sqlite3.Row, score: float | None = None) -> dict[str, Any]:
    payload = json.loads(row["payload_json"])
    tokens = _tokens(f"{row['title']} {row['body']}")
    return {
        "doc_id": row["doc_id"],
        "kind": row["kind"],
        "title": row["title"],
        "source_path": row["source_path"],
        "score": float(row["score"] if score is None and "score" in row.keys() else score or 0.0),
        "snippet": _snippet(row["body"], tokens[:8]),
        "payload": payload,
    }


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?",
        (name,),
    ).fetchone()
    return row is not None


def _tokens(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9_]{3,}", text.lower())
    seen = set()
    out = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            out.append(token)
    return out


def _token_score(tokens: list[str], text: str) -> int:
    lowered = text.lower()
    return sum(1 for token in tokens if token in lowered)


def _snippet(text: str, tokens: list[str], width: int = 240) -> str:
    if not text:
        return ""
    lowered = text.lower()
    positions = [lowered.find(token) for token in tokens if lowered.find(token) >= 0]
    start = min(positions) if positions else 0
    start = max(0, start - 40)
    snippet = " ".join(text[start : start + width].split())
    return snippet
