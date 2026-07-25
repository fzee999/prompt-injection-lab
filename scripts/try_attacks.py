"""Try attacks of one type against the undefended assistant and print what happened.

    .venv\\Scripts\\python scripts\\try_attacks.py direct
    .venv\\Scripts\\python scripts\\try_attacks.py direct --ids D01,D06
    .venv\\Scripts\\python scripts\\try_attacks.py leakage --full

This is a preview tool for writing attacks, not the experiment. The harness
(step 09) runs every attack under every defense setting and records the results.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.assistant import answer  # noqa: E402
from lab.attacks import load_attacks, needs_review, poison, succeeded  # noqa: E402
from lab.prompts import load_documents  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("type", choices=["direct", "indirect", "leakage"])
    p.add_argument("--ids", help="comma-separated attack ids to run; default all of the type")
    p.add_argument("--full", action="store_true", help="print whole replies, not the first line")
    args = p.parse_args()

    attacks = load_attacks(type=args.type)
    if args.ids:
        wanted = set(args.ids.split(","))
        attacks = [a for a in attacks if a.id in wanted]
    docs = load_documents()

    hits = 0
    for a in attacks:
        res = answer(a.prompt, docs=poison(docs, a), mode="all")
        ok = succeeded(a, res.text)
        review = ok and needs_review(res.text)
        hits += ok
        flag = "HIT " if ok else "miss"
        shown = res.text if args.full else res.text.splitlines()[0][:110] if res.text else "(empty)"
        print(f"[{flag}] {a.id} {a.technique:40} {res.result.seconds:4.1f}s  {shown}"
              + ("   <-- review: looks like a refusal" if review else ""))
    print(f"\n{hits}/{len(attacks)} {args.type} attacks succeeded against the baseline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
