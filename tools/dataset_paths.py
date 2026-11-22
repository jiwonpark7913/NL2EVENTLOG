"""Locate a dataset by its stable name under its provenance group."""
from pathlib import Path


def dataset_path(root: Path, name: str) -> Path:
    matches = [path for path in (root / "datasets").glob(f"*/{name}") if path.is_dir()]
    if len(matches) != 1:
        raise ValueError(f"Expected one dataset directory for {name!r}, found {len(matches)}")
    return matches[0]
