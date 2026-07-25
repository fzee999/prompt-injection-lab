"""Log the benign questions under every setting, the same way the harness logs attacks.

    .venv\\Scripts\\python scripts\\run_benign.py

Writes results/benign_<run_id>.csv with the same columns as the attack log:
type = "benign", goal = "utility", success = answered correctly (expected
fragments present, or the gap admitted for the unanswerable one). This is the
evidence behind the "7/7 under every setting" utility claim.
"""
from __future__ import annotations

import csv
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.benign import BENIGN, benign_ok  # noqa: E402
from lab.defenses import SETTINGS, answer_defended  # noqa: E402
from lab.harness import FIELDS, RESULTS_DIR, Row  # noqa: E402
from lab.prompts import load_documents  # noqa: E402


class _Q:
    type = "benign"

    def __init__(self, prompt: str):
        self.prompt = prompt


def main() -> int:
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    docs = load_documents()
    rows: list[Row] = []
    for setting in SETTINGS:
        for b in BENIGN:
            ans, blocked = answer_defended(_Q(b.question), docs, setting.config)
            ok = (not blocked) and benign_ok(b, ans.text)
            rows.append(Row(
                run_id=run_id, setting=setting.name, attack_id=b.id, type="benign",
                technique=b.question, goal="utility", success=ok, needs_review=False,
                blocked=blocked, prompt_tokens=ans.result.prompt_tokens,
                completion_tokens=ans.result.completion_tokens,
                seconds=round(ans.result.seconds, 2), model=ans.result.model, reply=ans.text,
            ))
            print(f"{setting.name:20} {b.id} {'ok  ' if ok else 'MISS'}", flush=True)
    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"benign_{run_id}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(asdict(r))
    correct = sum(r.success for r in rows)
    print(f"\n{correct}/{len(rows)} benign answers correct across {len(SETTINGS)} settings -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
