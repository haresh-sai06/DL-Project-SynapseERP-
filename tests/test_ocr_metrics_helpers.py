"""Unit tests for CER/WER helpers (no GPU / long train)."""
import importlib.util
from pathlib import Path

def _load():
    path = Path(__file__).resolve().parents[1] / "src" / "train_ledger_ocr.py"
    spec = importlib.util.spec_from_file_location("train_ledger_ocr", path)
    mod = importlib.util.module_from_spec(spec)
    # Avoid executing __main__; load for helpers only — helpers are module-level
    # But importing pulls torch via train() deps. Use exec of just the helper portion.
    src = path.read_text()
    # Extract helper functions by compiling the file with a stubbed train entry
    ns = {}
    exec(compile(src, str(path), "exec"), ns)
    return ns

def test_levenshtein_basic():
    ns = _load()
    assert ns["_levenshtein"]("kitten", "sitting") == 3
    assert ns["_levenshtein"]("abc", "abc") == 0
    assert ns["_levenshtein_seq"](["a", "b"], ["a", "c"]) == 1
