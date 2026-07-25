"""SQLite persistence for ResetPath.

The installed mobile app has no remote backend. This module is the complete
local persistence layer and stores data in Flet's app-private data directory.
"""

from __future__ import annotations

from contextlib import contextmanager
import csv
from datetime import date, datetime, timezone
from io import BytesIO, StringIO
import os
from pathlib import Path
import sqlite3
from typing import Any, Iterator
import zipfile

from logic import (
    SupportSettings,
    Task,
    ThoughtEntry,
    Track,
    build_evidence_statement,
)
from wellbeing import MoodCheckin, WearableImportRow, WearableReading


SCHEMA_VERSION = 2


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def resolve_database_path() -> Path:
    configured = os.environ.get("FLET_APP_STORAGE_DATA")
    if configured:
        data_dir = Path(configured)
    else:
        data_dir = Path(__file__).resolve().parent / ".flet" / "storage" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "resetpath.db"


class Database:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else resolve_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA secure_delete = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_metadata (
                    version INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    trusted_person_name TEXT,
                    trusted_person_phone TEXT,
                    counsellor_name TEXT,
                    counsellor_phone TEXT,
                    counsellor_details TEXT,
                    disclaimer_acknowledged_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    track TEXT NOT NULL CHECK (
                        track IN ('dsa', 'core_cs', 'project', 'applications')
                    ),
                    planned_date TEXT NOT NULL,
                    estimated_minutes INTEGER,
                    completed_at TEXT,
                    completion_note TEXT,
                    evidence_statement TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_planned_date
                    ON tasks(planned_date);
                CREATE INDEX IF NOT EXISTS idx_tasks_completed_at
                    ON tasks(completed_at);
                CREATE INDEX IF NOT EXISTS idx_tasks_track
                    ON tasks(track);

                CREATE TABLE IF NOT EXISTS thought_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thought TEXT NOT NULL,
                    emotion TEXT NOT NULL,
                    evidence_for TEXT NOT NULL,
                    evidence_against TEXT NOT NULL,
                    next_action TEXT NOT NULL,
                    grounded_response TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_thought_entries_created_at
                    ON thought_entries(created_at);

                CREATE TABLE IF NOT EXISTS wearable_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recorded_date TEXT NOT NULL,
                    sleep_hours REAL,
                    resting_heart_rate REAL,
                    hrv_ms REAL,
                    steps INTEGER,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(recorded_date, source)
                );

                CREATE INDEX IF NOT EXISTS idx_wearable_readings_date
                    ON wearable_readings(recorded_date);

                CREATE TABLE IF NOT EXISTS mood_checkins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recorded_at TEXT NOT NULL,
                    mood TEXT NOT NULL,
                    energy INTEGER NOT NULL CHECK (energy BETWEEN 1 AND 5),
                    note TEXT NOT NULL DEFAULT ''
                );

                CREATE INDEX IF NOT EXISTS idx_mood_checkins_recorded_at
                    ON mood_checkins(recorded_at);
                """
            )
            version_row = connection.execute(
                "SELECT version FROM schema_metadata LIMIT 1"
            ).fetchone()
            if version_row is None:
                connection.execute(
                    "INSERT INTO schema_metadata(version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )
            elif version_row["version"] == 1:
                connection.execute(
                    "UPDATE schema_metadata SET version = ?", (SCHEMA_VERSION,)
                )
            elif version_row["version"] != SCHEMA_VERSION:
                raise RuntimeError(
                    "This ResetPath database was created by an unsupported version."
                )

    def get_settings(self) -> SupportSettings:
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM settings WHERE id = 1").fetchone()
        if row is None:
            return SupportSettings()
        return SupportSettings(
            trusted_person_name=row["trusted_person_name"] or "",
            trusted_person_phone=row["trusted_person_phone"] or "",
            counsellor_name=row["counsellor_name"] or "",
            counsellor_phone=row["counsellor_phone"] or "",
            counsellor_details=row["counsellor_details"] or "",
            disclaimer_acknowledged_at=_parse_datetime(
                row["disclaimer_acknowledged_at"]
            ),
        )

    def save_settings(self, settings: SupportSettings) -> None:
        now = utc_now().isoformat()
        acknowledged = (
            settings.disclaimer_acknowledged_at.isoformat()
            if settings.disclaimer_acknowledged_at
            else None
        )
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO settings (
                    id, trusted_person_name, trusted_person_phone,
                    counsellor_name, counsellor_phone, counsellor_details,
                    disclaimer_acknowledged_at, created_at, updated_at
                )
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    trusted_person_name = excluded.trusted_person_name,
                    trusted_person_phone = excluded.trusted_person_phone,
                    counsellor_name = excluded.counsellor_name,
                    counsellor_phone = excluded.counsellor_phone,
                    counsellor_details = excluded.counsellor_details,
                    disclaimer_acknowledged_at =
                        excluded.disclaimer_acknowledged_at,
                    updated_at = excluded.updated_at
                """,
                (
                    settings.trusted_person_name.strip(),
                    settings.trusted_person_phone.strip(),
                    settings.counsellor_name.strip(),
                    settings.counsellor_phone.strip(),
                    settings.counsellor_details.strip(),
                    acknowledged,
                    now,
                    now,
                ),
            )

    def add_task(
        self,
        title: str,
        track: Track,
        planned_date: date,
        estimated_minutes: int | None = None,
    ) -> Task:
        now = utc_now().isoformat()
        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO tasks (
                    title, track, planned_date, estimated_minutes,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    title.strip(),
                    track.value,
                    planned_date.isoformat(),
                    estimated_minutes,
                    now,
                    now,
                ),
            )
            task_id = int(cursor.lastrowid)
        task = self.get_task(task_id)
        if task is None:
            raise RuntimeError("The new task could not be loaded.")
        return task

    def get_task(self, task_id: int) -> Task | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
        return _row_to_task(row) if row else None

    def update_task(
        self,
        task_id: int,
        title: str,
        track: Track,
        planned_date: date,
        estimated_minutes: int | None,
    ) -> bool:
        with self.connection() as connection:
            cursor = connection.execute(
                """
                UPDATE tasks
                SET title = ?, track = ?, planned_date = ?,
                    estimated_minutes = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    title.strip(),
                    track.value,
                    planned_date.isoformat(),
                    estimated_minutes,
                    utc_now().isoformat(),
                    task_id,
                ),
            )
            return cursor.rowcount > 0

    def delete_task(self, task_id: int) -> bool:
        with self.connection() as connection:
            cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return cursor.rowcount > 0

    def set_task_completed(
        self,
        task_id: int,
        completed: bool,
        completion_note: str = "",
    ) -> bool:
        task = self.get_task(task_id)
        if task is None:
            return False
        if completed:
            completed_at = utc_now().isoformat()
            note = completion_note.strip() or None
            evidence = build_evidence_statement(task.title, completion_note)
        else:
            completed_at = None
            note = None
            evidence = None
        with self.connection() as connection:
            cursor = connection.execute(
                """
                UPDATE tasks
                SET completed_at = ?, completion_note = ?,
                    evidence_statement = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    completed_at,
                    note,
                    evidence,
                    utc_now().isoformat(),
                    task_id,
                ),
            )
            return cursor.rowcount > 0

    def list_tasks(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        track: Track | None = None,
        completed: bool | None = None,
    ) -> list[Task]:
        clauses: list[str] = []
        parameters: list[Any] = []
        if date_from:
            clauses.append("planned_date >= ?")
            parameters.append(date_from.isoformat())
        if date_to:
            clauses.append("planned_date <= ?")
            parameters.append(date_to.isoformat())
        if track:
            clauses.append("track = ?")
            parameters.append(track.value)
        if completed is True:
            clauses.append("completed_at IS NOT NULL")
        elif completed is False:
            clauses.append("completed_at IS NULL")
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        query = (
            "SELECT * FROM tasks"
            f"{where} ORDER BY planned_date DESC, completed_at IS NOT NULL, id DESC"
        )
        with self.connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [_row_to_task(row) for row in rows]

    def save_thought_entry(
        self,
        thought: str,
        emotion: str,
        evidence_for: str,
        evidence_against: str,
        next_action: str,
        grounded_response: str,
    ) -> ThoughtEntry:
        created_at = utc_now().isoformat()
        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO thought_entries (
                    thought, emotion, evidence_for, evidence_against,
                    next_action, grounded_response, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    thought.strip(),
                    emotion.strip(),
                    evidence_for.strip(),
                    evidence_against.strip(),
                    next_action.strip(),
                    grounded_response.strip(),
                    created_at,
                ),
            )
            entry_id = int(cursor.lastrowid)
        entry = self.get_thought_entry(entry_id)
        if entry is None:
            raise RuntimeError("The new journal entry could not be loaded.")
        return entry

    def get_thought_entry(self, entry_id: int) -> ThoughtEntry | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM thought_entries WHERE id = ?", (entry_id,)
            ).fetchone()
        return _row_to_thought_entry(row) if row else None

    def list_thought_entries(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ThoughtEntry]:
        safe_limit = max(1, min(limit, 500))
        safe_offset = max(0, offset)
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM thought_entries
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (safe_limit, safe_offset),
            ).fetchall()
        return [_row_to_thought_entry(row) for row in rows]

    def load_progress_rows(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[dict[str, Any]]:
        clauses = ["completed_at IS NOT NULL"]
        parameters: list[Any] = []
        if date_from:
            clauses.append("date(completed_at) >= ?")
            parameters.append(date_from.isoformat())
        if date_to:
            clauses.append("date(completed_at) <= ?")
            parameters.append(date_to.isoformat())
        with self.connection() as connection:
            rows = connection.execute(
                f"""
                SELECT id, title, track, planned_date, estimated_minutes,
                       completed_at, completion_note, evidence_statement
                FROM tasks
                WHERE {' AND '.join(clauses)}
                ORDER BY completed_at ASC
                """,
                parameters,
            ).fetchall()
        return [dict(row) for row in rows]

    def import_wearable_rows(
        self,
        rows: tuple[WearableImportRow, ...],
    ) -> int:
        """Insert or update local wearable context by date and source."""
        now = utc_now().isoformat()
        imported = 0
        with self.connection() as connection:
            for row in rows:
                connection.execute(
                    """
                    INSERT INTO wearable_readings (
                        recorded_date, sleep_hours, resting_heart_rate,
                        hrv_ms, steps, source, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(recorded_date, source) DO UPDATE SET
                        sleep_hours = excluded.sleep_hours,
                        resting_heart_rate = excluded.resting_heart_rate,
                        hrv_ms = excluded.hrv_ms,
                        steps = excluded.steps,
                        created_at = excluded.created_at
                    """,
                    (
                        row.recorded_date.isoformat(),
                        row.sleep_hours,
                        row.resting_heart_rate,
                        row.hrv_ms,
                        row.steps,
                        row.source,
                        now,
                    ),
                )
                imported += 1
        return imported

    def list_wearable_readings(self, *, limit: int = 90) -> list[WearableReading]:
        safe_limit = max(1, min(limit, 370))
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM wearable_readings
                ORDER BY recorded_date DESC, id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [_row_to_wearable_reading(row) for row in rows]

    def save_mood_checkin(
        self,
        mood: str,
        energy: int,
        note: str = "",
    ) -> MoodCheckin:
        if not 1 <= energy <= 5:
            raise ValueError("Energy must be between 1 and 5.")
        clean_mood = mood.strip()[:40]
        if not clean_mood:
            raise ValueError("Choose a mood.")
        recorded_at = utc_now().isoformat()
        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO mood_checkins (recorded_at, mood, energy, note)
                VALUES (?, ?, ?, ?)
                """,
                (recorded_at, clean_mood, energy, note.strip()[:500]),
            )
            checkin_id = int(cursor.lastrowid)
            row = connection.execute(
                "SELECT * FROM mood_checkins WHERE id = ?", (checkin_id,)
            ).fetchone()
        if row is None:
            raise RuntimeError("The mood check-in could not be loaded.")
        return _row_to_mood_checkin(row)

    def list_mood_checkins(self, *, limit: int = 90) -> list[MoodCheckin]:
        safe_limit = max(1, min(limit, 370))
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM mood_checkins
                ORDER BY recorded_at DESC, id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [_row_to_mood_checkin(row) for row in rows]

    def create_export_zip(self) -> bytes:
        with self.connection() as connection:
            task_rows = connection.execute(
                """
                SELECT title, track, planned_date, estimated_minutes,
                       completed_at, completion_note, evidence_statement,
                       created_at, updated_at
                FROM tasks
                ORDER BY planned_date, id
                """
            ).fetchall()
            thought_rows = connection.execute(
                """
                SELECT thought, emotion, evidence_for, evidence_against,
                       next_action, grounded_response, created_at
                FROM thought_entries
                ORDER BY created_at, id
                """
            ).fetchall()
            wearable_rows = connection.execute(
                """
                SELECT recorded_date, sleep_hours, resting_heart_rate,
                       hrv_ms, steps, source, created_at
                FROM wearable_readings
                ORDER BY recorded_date, id
                """
            ).fetchall()
            mood_rows = connection.execute(
                """
                SELECT recorded_at, mood, energy, note
                FROM mood_checkins
                ORDER BY recorded_at, id
                """
            ).fetchall()

        task_csv = _rows_to_csv(task_rows)
        thought_csv = _rows_to_csv(thought_rows)
        archive = BytesIO()
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("tasks.csv", task_csv)
            zip_file.writestr("thought_journal.csv", thought_csv)
            zip_file.writestr("wearable_context.csv", _rows_to_csv(wearable_rows))
            zip_file.writestr("mood_checkins.csv", _rows_to_csv(mood_rows))
        return archive.getvalue()

    def delete_all_data(self) -> None:
        with self.connection() as connection:
            connection.execute("DELETE FROM thought_entries")
            connection.execute("DELETE FROM tasks")
            connection.execute("DELETE FROM wearable_readings")
            connection.execute("DELETE FROM mood_checkins")
            connection.execute("DELETE FROM settings")
        with self.connection() as connection:
            connection.execute("VACUUM")


def _parse_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _row_to_task(row: sqlite3.Row) -> Task:
    return Task(
        id=row["id"],
        title=row["title"],
        track=Track(row["track"]),
        planned_date=date.fromisoformat(row["planned_date"]),
        estimated_minutes=row["estimated_minutes"],
        completed_at=_parse_datetime(row["completed_at"]),
        completion_note=row["completion_note"],
        evidence_statement=row["evidence_statement"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _row_to_thought_entry(row: sqlite3.Row) -> ThoughtEntry:
    return ThoughtEntry(
        id=row["id"],
        thought=row["thought"],
        emotion=row["emotion"],
        evidence_for=row["evidence_for"],
        evidence_against=row["evidence_against"],
        next_action=row["next_action"],
        grounded_response=row["grounded_response"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_wearable_reading(row: sqlite3.Row) -> WearableReading:
    return WearableReading(
        id=row["id"],
        recorded_date=date.fromisoformat(row["recorded_date"]),
        sleep_hours=row["sleep_hours"],
        resting_heart_rate=row["resting_heart_rate"],
        hrv_ms=row["hrv_ms"],
        steps=row["steps"],
        source=row["source"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_mood_checkin(row: sqlite3.Row) -> MoodCheckin:
    return MoodCheckin(
        id=row["id"],
        recorded_at=datetime.fromisoformat(row["recorded_at"]),
        mood=row["mood"],
        energy=row["energy"],
        note=row["note"] or "",
    )


def _rows_to_csv(rows: list[sqlite3.Row]) -> str:
    output = StringIO(newline="")
    if not rows:
        return ""
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(dict(row) for row in rows)
    return output.getvalue()
