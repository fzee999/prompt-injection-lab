"""Turn a raw results CSV into the committed summary table and the chart.

    .venv\\Scripts\\python scripts\\aggregate.py                 # newest results/raw_*.csv
    .venv\\Scripts\\python scripts\\aggregate.py results/raw_X.csv

Writes:
  results/summary.csv  attack success RATE per setting x attack type (+ overall).
                       No replies, so it is safe to commit and is the deliverable.
  results/chart.png    grouped bars: success rate per setting, split by type.

Attack success rate (ASR) = successes / attacks, as a percentage. Lower is better.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RESULTS = Path(__file__).resolve().parent.parent / "results"
SETTING_ORDER = ["baseline", "D1_hardened_prompt", "D2_input_filter",
                 "D3_delimit_docs", "D4_output_check", "all_defenses"]
LABELS = {"baseline": "Baseline", "D1_hardened_prompt": "D1 prompt",
          "D2_input_filter": "D2 input", "D3_delimit_docs": "D3 delimit",
          "D4_output_check": "D4 output", "all_defenses": "All four"}
TYPES = ["direct", "indirect", "leakage"]
TYPE_COLOR = {"direct": "#4C72B0", "indirect": "#C44E52", "leakage": "#DD8452"}


def load(path: Path):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    # counts[setting][type] = [successes, total]
    counts: dict[str, dict[str, list[int]]] = {}
    for r in rows:
        s = counts.setdefault(r["setting"], {t: [0, 0] for t in TYPES})
        s[r["type"]][0] += r["success"] == "True"
        s[r["type"]][1] += 1
    return counts


def rate(cell: list[int]) -> float:
    return 100.0 * cell[0] / cell[1] if cell[1] else 0.0


def write_summary(counts, path: Path):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["setting", "direct_%", "indirect_%", "leakage_%", "overall_%",
                    "direct_n", "indirect_n", "leakage_n"])
        for s in SETTING_ORDER:
            c = counts[s]
            tot = [sum(c[t][0] for t in TYPES), sum(c[t][1] for t in TYPES)]
            w.writerow([s, f"{rate(c['direct']):.0f}", f"{rate(c['indirect']):.0f}",
                        f"{rate(c['leakage']):.0f}", f"{100*tot[0]/tot[1]:.0f}",
                        f"{c['direct'][0]}/{c['direct'][1]}",
                        f"{c['indirect'][0]}/{c['indirect'][1]}",
                        f"{c['leakage'][0]}/{c['leakage'][1]}"])


def draw_chart(counts, path: Path):
    settings = [s for s in SETTING_ORDER if s in counts]
    x = range(len(settings))
    width = 0.26
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for i, t in enumerate(TYPES):
        vals = [rate(counts[s][t]) for s in settings]
        bars = ax.bar([p + (i - 1) * width for p in x], vals, width,
                      label=t.capitalize(), color=TYPE_COLOR[t])
        for b, v in zip(bars, vals):
            if v > 0:
                ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.0f}",
                        ha="center", va="bottom", fontsize=8)
    ax.set_xticks(list(x))
    ax.set_xticklabels([LABELS[s] for s in settings])
    ax.set_ylabel("Attack success rate (%)  ·  lower is better")
    ax.set_ylim(0, 75)
    ax.set_title("Prompt-injection defenses vs attack type\nLlama 3.1 8B, 45 attacks per setting (n=15 per type)")
    ax.legend(title="Attack type")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else sorted(RESULTS.glob("raw_*.csv"))[-1]
    counts = load(src)
    write_summary(counts, RESULTS / "summary.csv")
    draw_chart(counts, RESULTS / "chart.png")
    print(f"source : {src.name}")
    print(f"wrote  : results/summary.csv, results/chart.png\n")
    print(open(RESULTS / "summary.csv", encoding="utf-8").read())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
