"""Small local inference helpers for ResetPath's optional AI layer.

The router classifies broad communication tone only. It is never used to
diagnose, determine safety, or override the deterministic crisis-language gate.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
from typing import Iterable

from logic import contains_crisis_language, normalize_text


@dataclass(frozen=True, slots=True)
class EmotionRoute:
    label: str
    confidence: float


def classify_emotion(text: str, artifact_path: Path | None = None) -> EmotionRoute | None:
    """Classify ordinary emotion language with the bundled linear model.

    Explicit crisis language intentionally returns ``None``. Callers must show
    human support instead of attempting any model-based response.
    """
    if contains_crisis_language(text):
        return None
    path = artifact_path or Path(__file__).resolve().parent / "assets" / "emotion_router.json"
    try:
        model = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    tokens = normalize_text(text).split()
    if not tokens:
        return None
    terms = tokens + [f"{left} {right}" for left, right in zip(tokens, tokens[1:])]
    counts = Counter(terms)
    vocabulary: dict[str, int] = model["vocabulary"]
    idf: list[float] = model["idf"]
    feature_count = len(vocabulary)
    vector: dict[int, float] = {}
    for term, count in counts.items():
        index = vocabulary.get(term)
        if index is not None:
            vector[index] = (1.0 + math.log(count)) * idf[index]
    if not vector:
        return None
    length = math.sqrt(sum(value * value for value in vector.values()))
    if not length:
        return None
    scores = []
    for intercept, weights in zip(model["intercepts"], model["coefficients"]):
        scores.append(float(intercept) + sum(weights[index] * value / length for index, value in vector.items()))
    maximum = max(scores)
    probabilities = [math.exp(score - maximum) for score in scores]
    total = sum(probabilities)
    probabilities = [score / total for score in probabilities]
    best_index = max(range(len(probabilities)), key=probabilities.__getitem__)
    confidence = probabilities[best_index]
    if confidence < float(model.get("minimum_confidence", 0.45)):
        return None
    return EmotionRoute(str(model["labels"][best_index]), round(confidence, 3))


def retrieve_diary_context(query: str, diary_pages: Iterable[str], limit: int = 3) -> tuple[str, ...]:
    """Return short relevant local excerpts, never a hidden long-term profile."""
    if contains_crisis_language(query):
        return ()
    query_terms = set(normalize_text(query).split())
    if not query_terms:
        return ()
    matches: list[tuple[int, str]] = []
    for page in diary_pages:
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", page):
            clean = sentence.strip()
            if len(clean) < 12 or contains_crisis_language(clean):
                continue
            score = len(query_terms.intersection(normalize_text(clean).split()))
            if score:
                matches.append((score, clean[:360]))
    matches.sort(key=lambda item: item[0], reverse=True)
    return tuple(text for _, text in matches[: max(1, min(limit, 3))])
