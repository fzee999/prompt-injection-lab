"""Settings for the lab, read once from the environment.

Anything that changes between runs lives here: which model is attacked, where
it is served, the key if the server wants one, and pacing. The rest of the code
calls `get_settings()` and never touches os.environ, so swapping the model is a
.env edit and nothing else.

Defaults point at a local Ollama server. To use OpenRouter instead, set
LAB_BASE_URL, LAB_MODEL and OPENROUTER_API_KEY in .env (see .env.example).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent  # the project folder
load_dotenv(ROOT / ".env")  # no-op when the file does not exist

OLLAMA_URL = "http://localhost:11434/v1"
OPENROUTER_URL = "https://openrouter.ai/api/v1"


@dataclass(frozen=True)
class Settings:
    base_url: str  # where the OpenAI-format API is served
    model: str  # the target model's name on that server
    api_key: str  # Ollama ignores it, but the client insists on a value
    provider: str | None  # OpenRouter only: pin one backend provider
    min_interval: float  # seconds between calls, for rate-limit pacing
    seed: int  # fixed sampling seed, for repeatable answers

    @property
    def is_local(self) -> bool:
        return "localhost" in self.base_url or "127.0.0.1" in self.base_url


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    base_url = _env("LAB_BASE_URL", OLLAMA_URL)
    # The 8k-context variant built from models/llama3.1-8b-8k.Modelfile (step 03).
    model = _env("LAB_MODEL", "llama3.1:8b-8k")
    local = "localhost" in base_url or "127.0.0.1" in base_url

    api_key = _env("OPENROUTER_API_KEY")
    if local:
        api_key = api_key or "ollama"
    elif not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set but LAB_BASE_URL is remote. "
            "Copy .env.example to .env and fill it in."
        )

    interval = _env("LAB_MIN_INTERVAL")
    if interval:
        min_interval = float(interval)
    else:
        min_interval = 3.0 if model.endswith(":free") else 0.0

    return Settings(
        base_url=base_url,
        model=model,
        api_key=api_key,
        provider=_env("LAB_PROVIDER") or None,
        min_interval=min_interval,
        seed=int(_env("LAB_SEED", "0")),
    )
