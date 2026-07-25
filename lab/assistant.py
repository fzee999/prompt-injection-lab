"""The target: a document Q&A assistant.

answer() builds the conversation the model sees and returns the reply with
bookkeeping. This is the thing the attacks are aimed at, so its shape is a
deliberate baseline (explained in docs/steps/03):

    system    : persona + rules + the secret          (BASELINE_SYSTEM_PROMPT)
    user      : "Policy documents:" + context block + "Question:" + the question
    assistant : the reply

The documents travel in the user turn, the way most retrieval-augmented
assistants inject retrieved text, so a poisoned document carries user-level
authority, not system-level. Two retrieval modes:

    "all"   every document, every time. Default for the experiment: deterministic,
            cache-friendly, and an attack never depends on retrieval luck.
    "topk"  the k documents whose words best match the question. The realistic
            mode for the interface; in a real system an attacker must also win
            retrieval before an indirect attack can fire.

Every knob a defense will need is a parameter: system_prompt (D1), the
document formatter (D3). Input filtering (D2) and output checking (D4) wrap
answer() from outside.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Callable

from .llm import ChatResult, Message, chat
from .prompts import BASELINE_SYSTEM_PROMPT, Document, format_documents, load_documents

Formatter = Callable[[list[Document]], str]

# Function words carry no signal about which document a question is about.
STOPWORDS = frozenset(
    """a an and are as at be by can could do does for from had has have how i if in
    into is it its may me my of on or our so than that the their them then there
    these they this to up was we were what when where which who will with would
    you your any all about out no not but""".split()
)
_word_re = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")


def tokens(text: str) -> list[str]:
    """Lower-cased words and numbers, minus stopwords and single characters."""
    return [w for w in _word_re.findall(text.lower()) if w not in STOPWORDS and len(w) > 1]


def select_documents(question: str, docs: list[Document], k: int = 2) -> list[Document]:
    """The k documents whose vocabulary best matches the question.

    Scoring is lexical and deterministic: each distinct question word found in a
    document adds an inverse-document-frequency weight, so a word that appears in
    every document ("university") counts for little and a word that appears in
    one ("citation") counts for a lot. Ties keep document order. If no document
    matches at all, every document is returned so the assistant can still say
    the answer is not there.
    """
    q_words = set(tokens(question))
    if not q_words:
        return list(docs)
    doc_words = [set(tokens(d.text)) for d in docs]
    df = Counter(w for words in doc_words for w in words)
    n = len(docs)

    def score(words: set[str]) -> float:
        return sum(math.log((n + 1) / (df[w] + 0.5)) + 1.0 for w in q_words if w in words)

    ranked = sorted(
        ((score(words), i) for i, words in enumerate(doc_words)),
        key=lambda t: (-t[0], t[1]),
    )
    chosen = [docs[i] for s, i in ranked[:k] if s > 0]
    return chosen or list(docs)


def build_messages(
    question: str,
    docs: list[Document],
    *,
    system_prompt: str = BASELINE_SYSTEM_PROMPT,
    formatter: Formatter = format_documents,
    history: list[Message] | None = None,
) -> list[Message]:
    """The exact conversation sent to the model.

    Documents come before the question inside the user turn so that every call
    with the same documents shares the same prefix and hits the server's cache.
    """
    user = f"Policy documents:\n\n{formatter(docs)}\n\nQuestion: {question}"
    return [
        {"role": "system", "content": system_prompt},
        *(history or []),
        {"role": "user", "content": user},
    ]


@dataclass(frozen=True)
class Answer:
    text: str
    documents: tuple[str, ...]  # titles of the documents the model was given
    result: ChatResult  # tokens, latency, model


def answer(
    question: str,
    *,
    docs: list[Document] | None = None,
    mode: str = "all",
    k: int = 2,
    system_prompt: str = BASELINE_SYSTEM_PROMPT,
    formatter: Formatter = format_documents,
    history: list[Message] | None = None,
    max_tokens: int = 300,
) -> Answer:
    """Answer one question from the documents. See the module docstring."""
    if mode not in ("all", "topk"):
        raise ValueError(f"mode must be 'all' or 'topk', not {mode!r}")
    docs = docs if docs is not None else load_documents()
    used = docs if mode == "all" else select_documents(question, docs, k)
    messages = build_messages(
        question, used, system_prompt=system_prompt, formatter=formatter, history=history
    )
    result = chat(messages, max_tokens=max_tokens)
    return Answer(text=result.text, documents=tuple(d.title for d in used), result=result)
