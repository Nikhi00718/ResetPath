"""Private wellbeing-context parsing and summaries.

Wearable data is deliberately treated as context.  This module does not create
stress scores, diagnoses, safety decisions, or medical recommendations.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from io import StringIO
import json
from typing import Any


@dataclass(frozen=True, slots=True)
class WearableReading:
    id: int
    recorded_date: date
    sleep_hours: float | None
    resting_heart_rate: float | None
    hrv_ms: float | None
    steps: int | None
    source: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class WearableImportRow:
    recorded_date: date
    sleep_hours: float | None
    resting_heart_rate: float | None
    hrv_ms: float | None
    steps: int | None
    source: str


@dataclass(frozen=True, slots=True)
class MoodCheckin:
    id: int
    recorded_at: datetime
    mood: str
    energy: int
    note: str


@dataclass(frozen=True, slots=True)
class ImportResult:
    rows: tuple[WearableImportRow, ...]
    errors: tuple[str, ...]


WEARABLE_TEMPLATE_HEADERS = (
    "date",
    "sleep_hours",
    "resting_heart_rate",
    "hrv_ms",
    "steps",
    "source",
)


def parse_wearable_file(file_name: str, data: bytes) -> ImportResult:
    """Parse a small CSV or JSON wearable export without network access."""
    if len(data) > 5_000_000:
        return ImportResult((), ("Choose a file smaller than 5 MB.",))
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return ImportResult((), ("Use a UTF-8 CSV or JSON file.",))

    try:
        if file_name.casefold().endswith(".json"):
            payload = json.loads(text)
            raw_rows = payload if isinstance(payload, list) else payload.get("readings", [])
            if not isinstance(raw_rows, list):
                raise ValueError("JSON must contain a list of readings.")
        else:
            raw_rows = list(csv.DictReader(StringIO(text)))
    except (csv.Error, json.JSONDecodeError, ValueError) as exc:
        return ImportResult((), (f"Could not read this file: {exc}",))

    parsed: list[WearableImportRow] = []
    errors: list[str] = []
    for index, raw in enumerate(raw_rows[:370], start=2):
        if not isinstance(raw, dict):
            errors.append(f"Row {index}: expected an object.")
            continue
        try:
            recorded_date = date.fromisoformat(str(raw.get("date", "")).strip())
            sleep = _optional_float(raw.get("sleep_hours"), 0, 24, "sleep_hours")
            heart_rate = _optional_float(
                raw.get("resting_heart_rate"), 20, 250, "resting_heart_rate"
            )
            hrv = _optional_float(raw.get("hrv_ms"), 1, 300, "hrv_ms")
            steps = _optional_int(raw.get("steps"), 0, 200_000, "steps")
            source = str(raw.get("source") or "Wearable export").strip()[:80]
            if all(value is None for value in (sleep, heart_rate, hrv, steps)):
                raise ValueError("add at least one measurement")
            parsed.append(
                WearableImportRow(
                    recorded_date,
                    sleep,
                    heart_rate,
                    hrv,
                    steps,
                    source,
                )
            )
        except (TypeError, ValueError) as exc:
            errors.append(f"Row {index}: {exc}.")
    if len(raw_rows) > 370:
        errors.append("Only the first 370 rows were imported.")
    return ImportResult(tuple(parsed), tuple(errors))


def wearable_template_csv() -> bytes:
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=WEARABLE_TEMPLATE_HEADERS)
    writer.writeheader()
    writer.writerow(
        {
            "date": date.today().isoformat(),
            "sleep_hours": "7.5",
            "resting_heart_rate": "68",
            "hrv_ms": "42",
            "steps": "6200",
            "source": "My watch export",
        }
    )
    return output.getvalue().encode("utf-8")


def _optional_float(
    value: Any,
    minimum: float,
    maximum: float,
    label: str,
) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    number = float(value)
    if not minimum <= number <= maximum:
        raise ValueError(f"{label} must be between {minimum:g} and {maximum:g}")
    return round(number, 2)


def _optional_int(
    value: Any,
    minimum: int,
    maximum: int,
    label: str,
) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    number = int(float(value))
    if not minimum <= number <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}")
    return number
