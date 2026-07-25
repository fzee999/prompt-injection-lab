"""The experiment: run every attack under every setting, score it, log every row.

One row per (setting, attack). The row holds the verdict AND the raw reply, so
the results can be re-scored later without re-running the model, and every claim
in the write-up traces back to a logged reply.
"""
from __future__ import annotations

import csv
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from .attacks import Attack, load_attacks, needs_review, poison, succeeded
from .config import ROOT, get_settings
from .defenses import SETTINGS, Setting, answer_defended
from .prompts import load_documents

RESULTS_DIR = ROOT / "results"

FIELDS = [
    "run_id", "setting", "attack_id", "type", "technique", "goal",
    "success", "needs_review", "blocked",
    "prompt_tokens", "completion_tokens", "seconds", "model", "reply",
]


@dataclass
class Row:
    run_id: str
    setting: str
    attack_id: str
    type: str
    technique: str
    goal: str
    success: bool
    needs_review: bool
    blocked: bool
    prompt_tokens: int
    completion_tokens: int
    seconds: float
    model: str
    reply: str


def run(
    attacks: list[Attack] | None = None,
    settings: list[Setting] | None = None,
    *,
    run_id: str | None = None,
    progress: bool = True,
) -> list[Row]:
    attacks = attacks if attacks is not None else load_attacks()
    settings = settings if settings is not None else SETTINGS
    run_id = run_id or datetime.now().strftime("%Y%m%d-%H%M%S")
    docs = load_documents()

    rows: list[Row] = []
    total = len(settings) * len(attacks)
    n = 0
    started = time.perf_counter()
    for setting in settings:
        for attack in attacks:
            n += 1
            corpus = poison(docs, attack)  # no-op for non-indirect attacks
            ans, blocked = answer_defended(attack, corpus, setting.config)
            ok = succeeded(attack, ans.text)
            rows.append(Row(
                run_id=run_id,
                setting=setting.name,
                attack_id=attack.id,
                type=attack.type,
                technique=attack.technique,
                goal=attack.goal,
                success=ok,
                needs_review=needs_review(ans.text) if attack.goal == "marker" else False,
                blocked=blocked,
                prompt_tokens=ans.result.prompt_tokens,
                completion_tokens=ans.result.completion_tokens,
                seconds=round(ans.result.seconds, 2),
                model=ans.result.model,
                reply=ans.text,
            ))
            if progress:
                flag = "HIT " if ok else "miss"
                print(f"[{n:3}/{total}] {setting.name:20} {attack.id:4} {flag}", flush=True)
    if progress:
        print(f"done in {time.perf_counter() - started:.0f}s")
    return rows


def write_csv(rows: list[Row], path: Path | None = None) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    run_id = rows[0].run_id if rows else datetime.now().strftime("%Y%m%d-%H%M%S")
    path = path or (RESULTS_DIR / f"raw_{run_id}.csv")
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
    return path
