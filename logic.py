"""Pure domain logic for ResetPath.

This module deliberately has no Flet or database imports. Safety interception,
validation, and text generation can therefore be tested in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from functools import lru_cache
import json
from pathlib import Path
import re
import unicodedata


class Track(StrEnum):
    DSA = "dsa"
    CORE_CS = "core_cs"
    PROJECT = "project"
    APPLICATIONS = "applications"

    @property
    def label(self) -> str:
        return {
            Track.DSA: "DSA",
            Track.CORE_CS: "Core CS",
            Track.PROJECT: "Project Development",
            Track.APPLICATIONS: "Applications",
        }[self]


@dataclass(frozen=True, slots=True)
class ValidationResult:
    is_valid: bool
    message: str = ""


@dataclass(frozen=True, slots=True)
class Task:
    id: int
    title: str
    track: Track
    planned_date: date
    estimated_minutes: int | None
    completed_at: datetime | None
    completion_note: str | None
    evidence_statement: str | None
    created_at: datetime
    updated_at: datetime

    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None


@dataclass(frozen=True, slots=True)
class ThoughtEntry:
    id: int
    thought: str
    emotion: str
    evidence_for: str
    evidence_against: str
    next_action: str
    grounded_response: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SupportSettings:
    trusted_person_name: str = ""
    trusted_person_phone: str = ""
    counsellor_name: str = ""
    counsellor_phone: str = ""
    counsellor_details: str = ""
    disclaimer_acknowledged_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class SupportPlan:
    """A deterministic, non-diagnostic response to one difficult thought."""

    acknowledgement: str
    grounded_reframe: str
    actions: tuple[str, str, str]
    evidence_for: str
    evidence_against: str
    source_id: str = "general"
    source_title: str = "A difficult moment"


CRISIS_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern)
    for pattern in (
        r"\bsuicide\b",
        r"\bsuicidal\b",
        r"\bkill myself\b",
        r"\bkilling myself\b",
        r"\bend my life\b",
        r"\bending my life\b",
        r"\btake my life\b",
        r"\btaking my life\b",
        r"\bhurt myself\b",
        r"\bhurting myself\b",
        r"\bharm myself\b",
        r"\bharming myself\b",
        r"\bself harm\b",
        r"\bdon t want to live\b",
        r"\bdo not want to live\b",
        r"\bno longer want to live\b",
        r"\bwish i (?:was|were) dead\b",
        r"\bwish to be dead\b",
        r"\bbetter off dead\b",
        r"\bno reason to live\b",
    )
)


def normalize_text(value: str) -> str:
    """Normalize free text for conservative phrase matching."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = normalized.replace("’", "'").replace("`", "'")
    normalized = re.sub(r"[^a-z0-9\s']", " ", normalized)
    normalized = normalized.replace("'", " ")
    return re.sub(r"\s+", " ", normalized).strip()


def contains_crisis_language(*values: str) -> bool:
    """Return True for explicit crisis phrases.

    This is only a redirect trigger. False must never be treated as evidence
    that a person is safe.
    """
    combined = normalize_text(" ".join(value for value in values if value))
    return any(pattern.search(combined) for pattern in CRISIS_PATTERNS)


def validate_task(
    title: str,
    track: Track | str,
    estimated_minutes: int | None,
) -> ValidationResult:
    clean_title = title.strip()
    if not clean_title:
        return ValidationResult(False, "Enter a small, specific task.")
    if len(clean_title) > 200:
        return ValidationResult(False, "Keep the task title under 200 characters.")
    try:
        Track(track)
    except ValueError:
        return ValidationResult(False, "Choose a valid progress track.")
    if estimated_minutes is not None and not 1 <= estimated_minutes <= 480:
        return ValidationResult(False, "Estimated minutes must be between 1 and 480.")
    return ValidationResult(True)


def validate_reflection(
    thought: str,
    emotion: str,
    evidence_for: str,
    evidence_against: str,
    next_action: str,
) -> ValidationResult:
    fields = {
        "thought": (thought, 2_000),
        "emotion": (emotion, 100),
        "supporting evidence": (evidence_for, 3_000),
        "balancing evidence": (evidence_against, 3_000),
        "next action": (next_action, 500),
    }
    for label, (value, maximum) in fields.items():
        if not value.strip():
            return ValidationResult(False, f"Add your {label}.")
        if len(value.strip()) > maximum:
            return ValidationResult(False, f"Keep {label} under {maximum:,} characters.")
    return ValidationResult(True)


def build_grounded_response(
    thought: str,
    emotion: str,
    evidence_for: str,
    evidence_against: str,
    next_action: str,
) -> str:
    """Build a deterministic response without inventing facts."""
    return (
        f'You are noticing {emotion.strip().lower()} and the thought '
        f'“{thought.strip()}”.\n\n'
        "Facts or experiences supporting this concern:\n"
        f"{evidence_for.strip()}\n\n"
        "Evidence that makes the feared conclusion less certain:\n"
        f"{evidence_against.strip()}\n\n"
        "One action within your control for the next ten minutes:\n"
        f"{next_action.strip()}"
    )


def build_support_plan(thought: str, emotion: str) -> SupportPlan:
    """Create a small contextual plan without diagnosing or inventing facts.

    This is the safe offline fallback used before any optional on-device model
    is installed.  The output is deliberately bounded to reflection and
    low-risk actions the user remains free to accept or ignore.
    """

    clean_thought = thought.strip()
    clean_emotion = emotion.strip() or "Uncertain"
    normalized = normalize_text(clean_thought)

    resource = retrieve_support_resource(normalized)
    reframe = resource["reframe"]
    actions = tuple(resource["actions"])

    if any(word in normalized.split() for word in ("never", "always", "nothing")):
        reframe += (
            " Your mind is using an absolute word; one painful moment cannot "
            "prove an absolute conclusion."
        )

    return SupportPlan(
        acknowledgement=(
            f"You’re noticing {clean_emotion.lower()} while your mind says "
            f"“{clean_thought}”."
        ),
        grounded_reframe=reframe,
        actions=actions,
        evidence_for=(
            f"This situation is bringing up {clean_emotion.lower()}, and it "
            "matters to you."
        ),
        evidence_against=reframe,
        source_id=resource["id"],
        source_title=resource["title"],
    )


def retrieve_support_resource(normalized_thought: str) -> dict[str, object]:
    """Retrieve one reviewed local support card using transparent token overlap."""
    resources = _load_support_library()
    thought_tokens = set(normalized_thought.split())
    best = next(item for item in resources if item["id"] == "general")
    best_score = 0
    for item in resources:
        keywords = set(item.get("keywords", []))
        score = len(thought_tokens.intersection(keywords))
        if score > best_score:
            best = item
            best_score = score
    return best


@lru_cache(maxsize=1)
def _load_support_library() -> tuple[dict[str, object], ...]:
    path = Path(__file__).resolve().parent / "assets" / "support_library.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list) or not payload:
            raise ValueError("support library is empty")
        return tuple(payload)
    except (OSError, json.JSONDecodeError, ValueError):
        return (
            {
                "id": "general",
                "title": "A difficult moment",
                "keywords": [],
                "reframe": (
                    "The feeling is real. The conclusion in the thought is not "
                    "automatically a confirmed fact."
                ),
                "actions": [
                    "Put both feet down and take three slow breaths",
                    "Write the smallest useful action you can do in ten minutes",
                    "Tell one trusted person that this is a hard moment",
                ],
            },
        )


def build_evidence_statement(task_title: str, completion_note: str = "") -> str:
    statement = f'I completed “{task_title.strip()}” today.'
    note = completion_note.strip()
    if note:
        statement = f"{statement} {note}"
    return statement


def normalize_phone_for_uri(value: str) -> str:
    """Keep a leading plus and digits for a tel URI."""
    value = value.strip()
    prefix = "+" if value.startswith("+") else ""
    digits = re.sub(r"\D", "", value)
    return f"{prefix}{digits}"


def validate_phone(value: str) -> ValidationResult:
    if not value.strip():
        return ValidationResult(True)
    normalized = normalize_phone_for_uri(value)
    digit_count = len(re.sub(r"\D", "", normalized))
    if not 7 <= digit_count <= 15:
        return ValidationResult(False, "Enter a valid phone number or leave it blank.")
    return ValidationResult(True)
