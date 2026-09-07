"""
Shared "bring your own dataset" utility.

Every milestone's upload endpoint uses this to accept a CSV/Excel file with
loosely-matching column names (a teammate's export, a Kaggle dataset, a
plant's own sensor log — whatever headers it happens to have) and map it
onto our internal schema. Nothing here is hardcoded to a specific dataset:
whatever numeric values are in the uploaded file are what get written to
the database, and every downstream KPI/model/chart recomputes from that —
same as the bundled default CSVs, just swapped for the user's own file.
"""
import pandas as pd
from pathlib import Path


def read_any(path) -> pd.DataFrame:
    """Read a CSV or Excel file transparently based on extension."""
    suffix = Path(path).suffix.lower()
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path)
    return pd.read_csv(path)


def resolve_columns(df: pd.DataFrame, aliases: dict[str, list[str]], required: set[str]) -> dict[str, str]:
    """Case/spacing-tolerant match of `aliases` (target field -> candidate
    header names) against the uploaded file's actual columns. Raises
    ValueError naming exactly which required field couldn't be found, so
    the frontend can show the user something actionable instead of a
    generic failure."""
    lower_map = {str(c).lower().strip(): c for c in df.columns}
    resolved = {}
    for target, alias_list in aliases.items():
        for alias in alias_list:
            if alias in lower_map:
                resolved[target] = lower_map[alias]
                break
    missing = required - set(resolved)
    if missing:
        raise ValueError(
            f"Could not find required column(s) {sorted(missing)} in the uploaded file. "
            f"Available columns: {list(df.columns)}"
        )
    return resolved


def save_upload_tmp(file, allowed_suffixes=(".csv", ".xlsx", ".xls")) -> Path:
    """Save a FastAPI UploadFile to a temp path, validating the extension
    first. Caller is responsible for deleting the returned path."""
    import shutil
    import tempfile
    from fastapi import HTTPException

    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed_suffixes:
        raise HTTPException(400, f"Only {', '.join(allowed_suffixes)} files are supported")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        return Path(tmp.name)
