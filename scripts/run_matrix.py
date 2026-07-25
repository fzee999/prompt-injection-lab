"""Run the attack x setting matrix and write the raw results CSV.

    .venv\\Scripts\\python scripts\\run_matrix.py             (all settings in defenses.SETTINGS)
    .venv\\Scripts\\python scripts\\run_matrix.py --smoke     (2 attacks x baseline, a quick wiring check)

On Day 1, defenses.SETTINGS is [baseline], so this produces the baseline run
(task 10). On Day 2 (task 21) the six settings are added and this is the full
matrix. Results go to results/raw_<run_id>.csv; a run_id ties every row together.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.attacks import load_attacks  # noqa: E402
from lab.config import get_settings  # noqa: E402
from lab.defenses import BASELINE, SETTINGS  # noqa: E402
from lab.harness import run, write_csv  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--smoke", action="store_true", help="2 attacks x baseline only")
    args = p.parse_args()

    print(f"model: {get_settings().model} at {get_settings().base_url}")
    if args.smoke:
        attacks = [a for a in load_attacks() if a.id in ("D01", "I06")]
        settings = [BASELINE]
    else:
        attacks = load_attacks()
        settings = SETTINGS
    print(f"{len(attacks)} attacks x {len(settings)} settings = {len(attacks) * len(settings)} calls\n")

    rows = run(attacks, settings)
    path = write_csv(rows)
    print(f"\nwrote {len(rows)} rows to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
