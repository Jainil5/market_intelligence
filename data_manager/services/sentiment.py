from __future__ import annotations

import re

_POSITIVE = re.compile(
    r"\b(surge|rally|gain|profit|growth|beat|upgrade|record|strong|bullish|dividend|expansion)\b",
    re.I,
)
_NEGATIVE = re.compile(
    r"\b(fall|drop|loss|decline|cut|downgrade|weak|bearish|fraud|probe|default|layoff|crash)\b",
    re.I,
)


def score_headline(text: str) -> str:
    """Lightweight rule-based sentiment for news headlines."""
    if not text:
        return "neutral"
    pos = len(_POSITIVE.findall(text))
    neg = len(_NEGATIVE.findall(text))
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"
