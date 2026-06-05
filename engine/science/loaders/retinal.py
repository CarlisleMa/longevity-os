"""Retinal imaging manifest parsers and lazy DICOM loader.

Covers 4 sub-modalities:
  - Structural OCT (15-col manifest, 56K records)
  - OCTA (47-col manifest, 24K records, cross-modal linking)
  - Photography — CFP, FAF, IR (11-col manifest, 94K records)
  - FLIO (10-col manifest, 8K records, 134 MB per file)

Design: parse manifests eagerly, load DICOM pixels lazily on demand.
"""

import ast
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import (
    DATA_ROOT, OCT_MANIFEST, OCTA_MANIFEST, PHOTO_MANIFEST, FLIO_MANIFEST,
)

_manifest_cache = {}


# ── Manifest loaders ───────────────────────────────────────────────────────

def _load_manifest(path, key) -> pd.DataFrame:
    if key in _manifest_cache:
        return _manifest_cache[key]
    df = pd.read_csv(path, sep="\t", dtype={"person_id": str}, low_memory=False)
    _manifest_cache[key] = df
    return df


def load_oct_manifest() -> pd.DataFrame:
    """Load retinal_oct/manifest.tsv (15 columns, 56K records)."""
    return _load_manifest(OCT_MANIFEST, "oct")


def load_octa_manifest() -> pd.DataFrame:
    """Load retinal_octa/manifest.tsv (47 columns, 24K records)."""
    return _load_manifest(OCTA_MANIFEST, "octa")


def load_photography_manifest() -> pd.DataFrame:
    """Load retinal_photography/manifest.tsv (11 columns, 94K records)."""
    return _load_manifest(PHOTO_MANIFEST, "photo")


def load_flio_manifest() -> pd.DataFrame:
    """Load retinal_flio/manifest.tsv (10 columns, 8K records)."""
    return _load_manifest(FLIO_MANIFEST, "flio")


# ── Per-person file listing ────────────────────────────────────────────────

def get_oct_files(person_id: str, device: str | None = None, laterality: str | None = None) -> pd.DataFrame:
    """Get OCT manifest rows for a participant, optionally filtered."""
    df = load_oct_manifest()
    mask = df["person_id"] == person_id
    if device:
        mask &= df["manufacturers_model_name"].str.contains(device, case=False)
    if laterality:
        mask &= df["laterality"] == laterality
    return df[mask].copy()


def get_octa_files(person_id: str, device: str | None = None, laterality: str | None = None) -> pd.DataFrame:
    """Get OCTA manifest rows for a participant, optionally filtered."""
    df = load_octa_manifest()
    mask = df["person_id"] == person_id
    if device:
        mask &= df["manufacturers_model_name"].str.contains(device, case=False)
    if laterality:
        mask &= df["laterality"] == laterality
    return df[mask].copy()


def get_photography_files(
    person_id: str,
    imaging_type: str | None = None,
    device: str | None = None,
    laterality: str | None = None,
) -> pd.DataFrame:
    """Get photography manifest rows. imaging_type: 'Color Photography', 'Infrared Reflectance', 'Autofluorescence'."""
    df = load_photography_manifest()
    mask = df["person_id"] == person_id
    if imaging_type:
        mask &= df["imaging"].str.contains(imaging_type, case=False)
    if device:
        mask &= df["manufacturers_model_name"].str.contains(device, case=False)
    if laterality:
        mask &= df["laterality"] == laterality
    return df[mask].copy()


def get_flio_files(person_id: str, wavelength: str | None = None, laterality: str | None = None) -> pd.DataFrame:
    """Get FLIO manifest rows. wavelength: 'Long wavelength' or 'Short wavelength'."""
    df = load_flio_manifest()
    mask = df["person_id"] == person_id
    if wavelength:
        mask &= df["wavelength"].str.contains(wavelength, case=False)
    if laterality:
        mask &= df["laterality"] == laterality
    return df[mask].copy()


# ── Lazy DICOM loading ─────────────────────────────────────────────────────


def _resolve_manifest_path(filepath: str | Path) -> Path:
    """Resolve AI-READI manifest paths to files under DATA_ROOT.

    Retinal manifests store dataset-relative paths with a leading slash, such as
    "/retinal_photography/...". Those look absolute to pathlib but are not
    filesystem-root paths on this cluster.
    """
    path = Path(filepath)
    if path.exists():
        return path
    return DATA_ROOT / str(path).lstrip("/")


def load_dicom(filepath: str) -> np.ndarray:
    """Load a DICOM file's pixel array.

    Args:
        filepath: relative path from manifest (e.g., '/retinal_oct/structural_oct/...')
                  or absolute path.

    Returns np.ndarray with shape depending on modality:
        OCT volume: (frames, height, width)
        OCTA flow cube: (frames, height, width)
        Photography/enface: (height, width) or (height, width, 3)
        FLIO: (frames, height, width) where frames=1024
    """
    import pydicom

    filepath = _resolve_manifest_path(filepath)

    ds = pydicom.dcmread(str(filepath))
    return ds.pixel_array


def load_dicom_metadata(filepath: str) -> dict:
    """Load DICOM metadata without loading pixel data."""
    import pydicom

    filepath = _resolve_manifest_path(filepath)

    ds = pydicom.dcmread(str(filepath), stop_before_pixels=True)
    return {
        "patient_id": str(getattr(ds, "PatientID", "")),
        "modality": str(getattr(ds, "Modality", "")),
        "manufacturer": str(getattr(ds, "Manufacturer", "")),
        "rows": int(getattr(ds, "Rows", 0)),
        "columns": int(getattr(ds, "Columns", 0)),
        "number_of_frames": int(getattr(ds, "NumberOfFrames", 1)),
        "bits_allocated": int(getattr(ds, "BitsAllocated", 0)),
        "sop_instance_uid": str(getattr(ds, "SOPInstanceUID", "")),
    }


# ── Cross-modal linking helpers ────────────────────────────────────────────

def get_octa_with_linked_files(person_id: str) -> pd.DataFrame:
    """Get OCTA rows with resolved paths to linked OCT, IR, segmentation, and enface files."""
    df = get_octa_files(person_id)
    # The OCTA manifest already contains cross-reference columns:
    #   associated_structural_oct_file_path, associated_retinal_photography_file_path,
    #   associated_segmentation_file_path, associated_enface_1-4_file_path
    return df


def parse_pixel_spacing(spacing_str: str) -> tuple[float, float] | None:
    """Parse pixel_spacing from manifest string like '[0.003872, 0.01206]'."""
    if not spacing_str or spacing_str == "Not reported":
        return None
    try:
        parsed = ast.literal_eval(spacing_str)
        if isinstance(parsed, list) and len(parsed) == 2:
            return (float(parsed[0]), float(parsed[1]))
    except (ValueError, SyntaxError):
        pass
    return None
