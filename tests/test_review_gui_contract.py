"""Static tests for the reviewer dashboard and its evidence-boundary contract."""
from __future__ import annotations
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "tools/review_gui/app.py"

def main():
    source = APP.read_text(encoding="utf-8")
    ast.parse(source, filename=str(APP))
    assert "file_uploader" in source
    assert "review/eeg/actual_eeg.json" in source
    assert "graphviz_chart" in source
    assert "Gold" in source
    # The UI must not execute SQL modifications or fabricate Step 1 graph nodes.
    assert "INSERT INTO" not in source
    assert "DELETE FROM" not in source
    assert "UPDATE " not in source
    assert "CREATE TABLE" not in source
    assert "model input" in source.lower()
    assert "read-only" in source.lower()
    for path in ("tools/review_gui/README.md", "tools/review_gui/CODEX_EEG_INTEGRATION.md"):
        assert (ROOT / path).exists()
    # Verify the intended four dataset choices and do not confuse the four synthetic datasets.
    for slug in ("mimic", "adventureworks", "bpi2019_ocel", "order_management_ocel"):
        assert slug in source
    # Basic actual EEG adapter node shape is documented rather than injected as runtime results.
    guide = (ROOT / "tools/review_gui/README.md").read_text(encoding="utf-8")
    assert "actual_eeg.json" in guide and "example above is illustrative only" in guide
    print("EEG review GUI static contract: OK")

if __name__ == "__main__":
    main()
