"""Test one defense configuration against the baseline: attack success and utility.

    .venv\\Scripts\\python scripts\\try_defense.py --d1          # hardened prompt only
    .venv\\Scripts\\python scripts\\try_defense.py --d4          # output check only
    .venv\\Scripts\\python scripts\\try_defense.py --d1 --d2 --d3 --d4   # all on

Prints attack success by type (this config vs baseline) and utility (benign
questions answered correctly). Used to build and check each Day 2 defense before
the full matrix (task 21).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.attacks import load_attacks, poison, succeeded  # noqa: E402
from lab.benign import BENIGN, benign_ok  # noqa: E402
from lab.defenses import DefenseConfig, answer_defended  # noqa: E402
from lab.prompts import load_documents  # noqa: E402
from lab.assistant import answer  # noqa: E402
from lab.defenses import formatter_for, system_prompt_for  # noqa: E402


def attack_success(config: DefenseConfig, attacks, docs):
    by = {"direct": [0, 0], "indirect": [0, 0], "leakage": [0, 0]}
    for a in attacks:
        ans, _ = answer_defended(a, poison(docs, a), config)
        by[a.type][0] += succeeded(a, ans.text)
        by[a.type][1] += 1
    return by


def utility(config: DefenseConfig, docs):
    ok = 0
    for b in BENIGN:
        ans, blocked = answer_defended(
            _as_attack(b.question), docs, config
        )
        ok += (not blocked) and benign_ok(b, ans.text)
    return ok, len(BENIGN)


class _Q:
    """Minimal attack-shaped object so benign questions use the same path."""
    type = "benign"
    def __init__(self, prompt): self.prompt = prompt


def _as_attack(prompt):
    return _Q(prompt)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    for d, help_ in [("d1", "hardened prompt"), ("d2", "input filter"),
                     ("d3", "delimit docs"), ("d4", "output check")]:
        p.add_argument(f"--{d}", action="store_true", help=help_)
    args = p.parse_args()

    config = DefenseConfig(args.d1, args.d2, args.d3, args.d4)
    base = DefenseConfig()
    attacks = load_attacks()
    docs = load_documents()

    on = [n for n, v in [("D1", args.d1), ("D2", args.d2), ("D3", args.d3), ("D4", args.d4)] if v] or ["none"]
    print(f"config: {'+'.join(on)}\n")

    b = attack_success(base, attacks, docs)
    c = attack_success(config, attacks, docs)
    print(f"{'type':10} {'baseline':>10} {'this':>10}")
    for t in ("direct", "indirect", "leakage"):
        print(f"{t:10} {b[t][0]}/{b[t][1]:>8} {c[t][0]}/{c[t][1]:>8}")
    bt = sum(v[0] for v in b.values()); ct = sum(v[0] for v in c.values()); n = sum(v[1] for v in b.values())
    print(f"{'TOTAL':10} {bt}/{n:>8} {ct}/{n:>8}")

    ub, _ = utility(base, docs)
    uc, un = utility(config, docs)
    print(f"\nutility (benign correct): baseline {ub}/{un}  this {uc}/{un}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
