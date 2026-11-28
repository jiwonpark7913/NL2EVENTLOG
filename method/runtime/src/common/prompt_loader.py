"""Load one prompt per file, preserving whitespace and examples."""

from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPT_ROOT = PROJECT_ROOT / "prompts"


def load_prompt(stage: str, name: str) -> str:
    """PURPOSE: Read one stage's centrally managed prompt as UTF-8.
    INPUT: Stage directory and filename stem, both simple path components.
    OUTPUT: Exact prompt text; rejects traversal and raises for missing files.
    """
    if stage not in {"step1_understand", "step2_retrieve_and_interpret", "step3_execute"}:
        raise ValueError(f"Unknown prompt stage: {stage}")
    if not name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_" for c in name):
        raise ValueError("Prompt names must contain lowercase letters, digits, or underscores")
    return (PROMPT_ROOT / stage / f"{name}.md").read_text(encoding="utf-8")
