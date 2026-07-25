# ResetPath Architecture and Backend

## 1. System overview

ResetPath is a single-process, offline-first mobile application.

```text
Flet screens
    │
    ├── validation and safety rules ── logic.py
    │
    └── typed repository operations ── database.py
                                           │
                                           └── resetpath.db
```

There is no web backend in version 1. In this project, “backend” means the local
Python domain logic and SQLite persistence layer running inside the installed
application.

## 2. File responsibilities

### `app.py`

Responsible for:

- starting Flet,
- application routing,
- responsive screen layouts,
- form state,
- calling validation and database operations,
- breathing animation and timing,
- file-export interaction,
- opening `tel:` and HTTPS links,
- and displaying user-safe errors.

It must not contain raw SQL or maintain a second copy of safety phrases.

### `database.py`

Responsible for:

- locating the app data directory,
- opening SQLite connections,
- creating and migrating the schema,
- task operations,
- journal operations,
- settings operations,
- progress queries,
- exports,
- and delete-all transactions.

It must not import Flet UI controls.

### `logic.py`

Responsible for pure, testable functions:

- input normalization,
- crisis-language interception,
- task validation,
- grounded-response creation,
- evidence-statement creation,
- phone-number normalization for dialler links,
- and progress date-range helpers.

It must not read from SQLite or display UI.

## 3. Storage location

Use:

```text
FLET_APP_STORAGE_DATA/resetpath.db
```

Flet provides this directory as durable app-private storage. In development,
Flet maps it to the project’s `.flet/storage/data` directory. See the
[Flet file-storage guide](https://flet.dev/docs/cookbook/read-and-write-files/).

Do not place the database:

- beside the packaged source files,
- in cache storage,
- in temporary storage,
- in the Git repository,
- or in a publicly shared downloads folder.

## 4. SQLite connection policy

Every connection enables:

```sql
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
PRAGMA secure_delete = ON;
```

Additional rules:

- use `sqlite3.Row` for named columns,
- use context managers for commits and rollback,
- use parameterized SQL for all user data,
- close connections promptly,
- store timestamps in ISO 8601 form,
- and use the device’s local date for “today.”

The app is single-user, so a remote database, connection pool, and API server
are unnecessary.

## 5. Database schema

### Schema metadata

```sql
CREATE TABLE schema_metadata (
    version INTEGER NOT NULL
);
```

The first downloadable release uses schema version `2`. Databases created by
the earlier prototype migrate from version 1 during startup. Future schema
changes use explicit, ordered migrations.

### Settings

```sql
CREATE TABLE settings (
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
```

There is at most one settings row.

### Tasks

```sql
CREATE TABLE tasks (
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
```

Recommended indexes:

```sql
CREATE INDEX idx_tasks_planned_date ON tasks(planned_date);
CREATE INDEX idx_tasks_completed_at ON tasks(completed_at);
CREATE INDEX idx_tasks_track ON tasks(track);
```

Validation:

- title: 1–200 trimmed characters,
- track: one of the four declared values,
- planned date: valid ISO date,
- estimated minutes: optional integer from 1 to 480,
- completion note: optional, maximum 1,000 characters.

### Thought entries

```sql
CREATE TABLE thought_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thought TEXT NOT NULL,
    emotion TEXT NOT NULL,
    evidence_for TEXT NOT NULL,
    evidence_against TEXT NOT NULL,
    next_action TEXT NOT NULL,
    grounded_response TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

Recommended index:

```sql
CREATE INDEX idx_thought_entries_created_at
ON thought_entries(created_at);
```

### Wearable context and mood check-ins

Schema version 2 adds `wearable_readings` and `mood_checkins`. Wearable rows are
unique by date and source so importing an updated export replaces that day's
values instead of silently duplicating them. Mood energy is constrained to
1–5. Both tables are included in export and delete-all.

These records are descriptive context only. The backend does not calculate a
stress score, diagnosis, or safety classification from them.

Suggested limits:

- thought: 2,000 characters,
- emotion: 100 characters,
- each evidence field: 3,000 characters,
- next action: 500 characters,
- generated response: 10,000 characters.

## 6. Typed domain objects

Use a string enum:

```text
Track.DSA
Track.CORE_CS
Track.PROJECT
Track.APPLICATIONS
```

Use dataclasses:

```text
Task
ThoughtEntry
SupportSettings
ValidationResult
```

Database rows are converted to typed objects before reaching the UI.

## 7. Database interface

The `Database` class exposes:

```text
initialize()
get_settings()
save_settings(settings)
add_task(task_input)
update_task(task_id, task_input)
delete_task(task_id)
set_task_completed(task_id, completed, completion_note)
list_tasks(date_from, date_to, track, completed)
save_thought_entry(entry)
list_thought_entries(limit, offset)
load_progress_rows(date_from, date_to)
create_export_zip()
delete_all_data()
```

Unknown IDs return a controlled “not found” result rather than crashing.

## 8. Grounded-response backend

Version 1 does not use AI. `logic.py` creates the response from a fixed template:

```text
You are noticing [emotion] and the thought “[thought]”.

Facts or experiences supporting this concern:
[evidence_for]

Evidence that makes the feared conclusion less certain:
[evidence_against]

One action within your control for the next ten minutes:
[next_action]
```

The function:

- never inserts evidence not supplied by the user,
- never predicts a placement result,
- never diagnoses the user,
- and returns plain text suitable for saving.

## 9. Evidence generation

When a task is completed:

```text
I completed “[task title]” today.
```

With a completion note:

```text
I completed “[task title]” today. [completion note]
```

Store the final evidence statement when completion occurs. This preserves
historical evidence even if the task title changes later.

When a completed task is reopened:

- clear `completed_at`,
- clear `evidence_statement`,
- retain or clear the completion note according to the user’s edit action.

## 10. Progress analysis

`database.py` returns completed task rows. Pandas performs:

- daily task counts,
- weekly task counts,
- totals by track,
- estimated-minute totals,
- seven-day and thirty-day filtering.

Flet Charts renders the aggregated result. Empty datasets show a helpful empty
state rather than a chart error.

## 11. Export

Create:

```text
resetpath-export-YYYYMMDD-HHMM.zip
```

It contains:

```text
tasks.csv
thought_journal.csv
```

Rules:

- use UTF-8 CSV,
- include headers,
- exclude trusted-person and counsellor settings,
- create the archive in temporary storage,
- pass its bytes to the native save/share service,
- delete the temporary archive after the action completes.

Warn the user that exported files may contain sensitive information and are no
longer protected by the application sandbox.

## 12. Delete all data

Deletion requires:

1. opening Settings,
2. pressing Delete All Data,
3. reading the warning,
4. typing `DELETE`,
5. pressing the final confirmation.

Inside one transaction:

- delete thought entries,
- delete tasks,
- delete settings.

After commit, compact the database and return to onboarding. Document that this
cannot guarantee forensic erasure from flash storage or erase previously
exported copies.

## 13. Error handling

User-facing errors must be short and actionable:

- “The task could not be saved. Please try again.”
- “That task no longer exists.”
- “Export was cancelled.”
- “No phone number has been configured.”

Detailed exceptions may be written to local development logs, but journal text
must not be included in error messages or analytics.
