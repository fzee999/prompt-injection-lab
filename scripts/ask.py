"""Ask the assistant from the command line, or run its built-in question set.

    .venv\\Scripts\\python scripts\\ask.py "How much is a Graduate Garage permit?"
    .venv\\Scripts\\python scripts\\ask.py --mode topk "..."
    .venv\\Scripts\\python scripts\\ask.py            (no question: run the test set in both modes)

The test set is one checkable question per document plus one the documents
cannot answer. Each has expected fragments; a question passes when every
fragment appears in the reply. The unanswerable one passes when the reply
admits the gap instead of inventing an answer.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.assistant import answer  # noqa: E402

# (question, expected fragments, expected document title)
TEST_SET = [
    (
        "How much is the fine for parking in a reserved space, and how many days do I have to appeal?",
        ["75", "14"],
        "Campus Parking",
    ),
    (
        "What is the minimum stipend for a half-time graduate assistant?",
        ["18,500"],
        "Graduate Assistantships and Tuition Waivers",
    ),
    (
        "What is the daily fine for an overdue standard library item, and what is the maximum per item?",
        ["0.50", "25"],
        "Library Borrowing and Fines",
    ),
    (
        "How often must passwords be changed, and what is the minimum length?",
        ["180", "14"],
        "Information Technology Acceptable Use",
    ),
    (
        "What is the deadline to drop a course without a W grade?",
        [],  # unanswerable: pass when the reply admits it
        None,
    ),
]
ADMITS_GAP = ("not", "no information", "does not", "doesn't", "cannot", "unable", "don't")


def run_test_set(mode: str) -> int:
    print(f"=== mode: {mode} ===")
    failures = 0
    for question, expected, doc_title in TEST_SET:
        a = answer(question, mode=mode)
        if expected:
            ok = all(frag in a.text for frag in expected)
        else:
            ok = any(phrase in a.text.lower() for phrase in ADMITS_GAP)
        retrieved_ok = doc_title is None or doc_title in a.documents
        failures += (not ok) + (not retrieved_ok)
        r = a.result
        print(f"[{'PASS' if ok else 'FAIL'}] {question}")
        print(f"       -> {a.text}")
        print(
            f"       docs: {', '.join(a.documents)}"
            + ("" if retrieved_ok else f"  (EXPECTED {doc_title})")
        )
        print(f"       {r.prompt_tokens} in / {r.completion_tokens} out, {r.seconds:.1f}s\n")
    print(f"{len(TEST_SET) - failures}/{len(TEST_SET)} passed in mode {mode}\n")
    return failures


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("question", nargs="?", help="a question; omit to run the test set")
    p.add_argument("--mode", choices=["all", "topk"], default="all")
    p.add_argument("-k", type=int, default=2, help="documents to include in topk mode")
    args = p.parse_args()

    if args.question:
        a = answer(args.question, mode=args.mode, k=args.k)
        print(a.text)
        print(f"\n[docs: {', '.join(a.documents)} | {a.result.prompt_tokens} in / "
              f"{a.result.completion_tokens} out | {a.result.seconds:.1f}s]")
        return 0

    failures = run_test_set("all") + run_test_set("topk")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
