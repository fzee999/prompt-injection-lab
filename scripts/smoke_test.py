"""Task 1's finish line: one working call to the configured model.

Run from the project folder:
    .venv\\Scripts\\python scripts\\smoke_test.py

Prints where the request went, which model answered, token counts, latency
and the reply. Exit code 0 on PASS.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `lab` importable

from openai import APIConnectionError, APIStatusError  # noqa: E402

from lab.config import get_settings  # noqa: E402
from lab.llm import chat  # noqa: E402


def main() -> int:
    s = get_settings()
    print(f"base_url : {s.base_url}")
    print(f"model    : {s.model}")
    try:
        r = chat(
            [
                {"role": "system", "content": "You are a concise assistant."},
                {"role": "user", "content": "Reply with exactly the two words: LAB OK"},
            ],
            max_tokens=20,
        )
    except APIConnectionError:
        where = "Ollama (is it running? start the Ollama app)" if s.is_local else s.base_url
        print(f"FAIL: could not connect to {where}")
        return 1
    except APIStatusError as e:
        print(f"FAIL: server answered HTTP {e.status_code}: {e.message}")
        if s.is_local:
            print("      (is the model pulled? run: ollama list)")
        else:
            print("      (a model id can disappear from OpenRouter; try an alternate from .env.example)")
        return 1

    via = f" via {r.provider}" if r.provider else ""
    print(f"answered : {r.model}{via}")
    print(f"tokens   : {r.prompt_tokens} in / {r.completion_tokens} out, {r.seconds:.1f}s")
    print(f"reply    : {r.text!r}")
    ok = "LAB OK" in r.text.upper()
    print("PASS" if ok else "FAIL: unexpected reply")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
