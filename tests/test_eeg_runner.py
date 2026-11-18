"""Tests for EEG adapter provenance and missing runtime behavior."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools/review_gui"))
from run_eeg import execute,validate_graph

def main():
    actual={"dataset":"mimic","source":"actual_step1_eeg",
            "generator_version":"fixture-only-test",
            "nodes":[{"id":"t1","type":"table","label":"admissions"}],
            "edges":[]}
    assert validate_graph(actual,"mimic")==actual
    for invalid in (
       dict(actual,source="gold_reference"),
       dict(actual,nodes=[{"id":"t1"},{"id":"t1"}]),
       dict(actual,edges=[{"source":"t1","target":"unknown"}]),
       dict(actual,dataset="adventureworks"),
       dict(actual,generator_version=""),
    ):
        try:
            validate_graph(invalid,"mimic")
        except ValueError:
            pass
        else:
            raise AssertionError(f"Graph should have been rejected: {invalid}")
    try:
        execute("mimic",runner="")
    except RuntimeError as e:
        assert "BLOCKED_NO_RUNTIME" in str(e)
    else:
        raise AssertionError("Missing actual EEG runtime must not succeed")
    print("EEG runtime integration contract tests: OK")

if __name__=="__main__":
    main()
