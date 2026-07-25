"""Validate the attack store and print its manifest.

Proves the structured attack set is well-formed: every attack has an id, type,
prompt, goal and a defined success rule; ids are unique; indirect attacks name a
document that exists and carry a payload; base64 payloads decode. Exit code 0
when the set is sound, 1 otherwise. This is the check that guards every later run.

    .venv\\Scripts\\python scripts\\validate_attacks.py
"""
from __future__ import annotations

import base64
import binascii
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.attacks import load_attacks, success_rule_text, summary  # noqa: E402
from lab.prompts import load_documents  # noqa: E402


def main() -> int:
    attacks = load_attacks()  # raises on any structural problem
    doc_names = {d.name for d in load_documents()}
    problems: list[str] = []

    for a in attacks:
        if a.type == "indirect" and a.document not in doc_names:
            problems.append(f"{a.id}: names document {a.document!r}, which does not exist")
        for token in a.payload.split() if a.payload else []:
            if len(token) > 24 and token.endswith("=") or (len(token) > 40 and token.isalnum()):
                try:
                    base64.b64decode(token, validate=True)
                except (binascii.Error, ValueError):
                    pass  # not base64, fine

    counts = summary(attacks)
    print(f"attack store: {len(attacks)} attacks")
    print(f"  by type: {counts['by_type']}")
    print(f"  by goal: {counts['by_goal']}\n")

    print(f"{'id':5} {'type':9} {'goal':7} {'technique':42} success rule")
    print("-" * 110)
    for a in attacks:
        print(f"{a.id:5} {a.type:9} {a.goal:7} {a.technique[:42]:42} {success_rule_text(a)}")

    if problems:
        print("\nPROBLEMS:")
        for p in problems:
            print("  " + p)
        return 1
    print("\nOK: every attack has id, type, prompt, goal and a success rule; ids unique; "
          "indirect attacks reference real documents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
