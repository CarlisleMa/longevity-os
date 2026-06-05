"""OMOP concept_id → human-readable label mapping.

Builds lookup dicts from measurement_source_value and observation_source_value
fields, which encode: "redcap_field, Human Readable Label".
"""

_cache = {}


def _extract_label(source_value: str) -> str:
    """Extract human-readable label from source_value like 'field_code, Label Text'."""
    if not isinstance(source_value, str):
        return str(source_value)
    parts = source_value.split(", ", 1)
    return parts[1].strip() if len(parts) > 1 else source_value.strip()


def _extract_field_code(source_value: str) -> str:
    """Extract REDCap field code from source_value."""
    if not isinstance(source_value, str):
        return str(source_value)
    parts = source_value.split(", ", 1)
    return parts[0].strip()


def build_concept_map(table: str = "measurement") -> dict[int, str]:
    """Build concept_id → human label dict from a clinical table.

    Uses clinical.py's cached DataFrames rather than re-reading from disk.

    Args:
        table: 'measurement', 'observation', or 'condition'

    Returns dict mapping concept_id (int) → label (str).
    """
    cache_key = f"concept_map_{table}"
    if cache_key in _cache:
        return _cache[cache_key]

    from ..loaders.clinical import load_measurements, load_observations, load_conditions

    if table == "measurement":
        df = load_measurements()
        id_col = "measurement_concept_id"
        src_col = "measurement_source_value"
    elif table == "observation":
        df = load_observations()
        id_col = "observation_concept_id"
        src_col = "observation_source_value"
    elif table == "condition":
        df = load_conditions()
        id_col = "condition_concept_id"
        src_col = "condition_source_value"
    else:
        raise ValueError(f"Unknown table: {table}. Valid: measurement, observation, condition")

    mapping = {}
    for concept_id, group in df.groupby(id_col):
        src = group[src_col].dropna().iloc[0] if not group[src_col].dropna().empty else ""
        mapping[int(concept_id)] = _extract_label(src)

    _cache[cache_key] = mapping
    return mapping


def get_concept_label(concept_id: int, table: str = "measurement") -> str:
    """Get human label for a concept_id."""
    mapping = build_concept_map(table)
    return mapping.get(concept_id, f"Unknown({concept_id})")


def search_concepts(query: str, table: str = "measurement") -> dict[int, str]:
    """Search for concepts matching a query string (case-insensitive)."""
    mapping = build_concept_map(table)
    q = query.lower()
    return {k: v for k, v in mapping.items() if q in v.lower()}
