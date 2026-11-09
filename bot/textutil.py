from __future__ import annotations

import re
import unicodedata


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def normalize(text: str) -> str:
    cleaned = strip_accents(text).lower().strip()
    return re.sub(r"\s+", " ", cleaned)


def contains_phrase(text: str, phrase: str) -> bool:
    return (
        text == phrase
        or text.startswith(phrase + " ")
        or text.endswith(" " + phrase)
        or f" {phrase} " in text
    )


def split_telegram(text: str, limit: int = 3900) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    current: list[str] = []
    size = 0
    for block in text.split("\n\n"):
        extra = len(block) if not current else len(block) + 2
        if current and size + extra > limit:
            parts.append("\n\n".join(current))
            current = [block]
            size = len(block)
        else:
            current.append(block)
            size += extra
    if current:
        parts.append("\n\n".join(current))
    return parts
