# ResetPath Step-by-Step Implementation

## Phase 1: Prepare the repository

Open PowerShell:

```powershell
cd "C:\Users\atnik\Documents\Support app"
git status
```

Create a development branch:

```powershell
git switch -c codex/resetpath-v1
```

Create the planned files and folders. Add `.gitignore` entries for:

```text
.venv/
__pycache__/
*.pyc
.flet/
build/
dist/
*.db
*.db-wal
*.db-shm
*.jks
.env
*.zip
```

Do not ignore the source icons under `assets/`.

## Phase 2: Create a virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If script execution is blocked:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Install dependencies after creating `requirements.txt`:

```powershell
python -m pip install -r requirements.txt
```

Verify:

```powershell
python -c "import flet, pandas; print('Dependencies installed')"
flet --version
```

## Phase 3: Implement `logic.py`

Implement in this order:

1. Track enum.
2. Dataclasses and validation result.
3. Text normalization.
4. Crisis phrase constant.
5. Crisis interception function.
6. Task validation.
7. Grounded-response template.
8. Evidence-statement generator.
9. Date-range helpers.

Keep the functions pure so tests do not need Flet or SQLite.

Run:

```powershell
python -m unittest tests.test_logic -v
```

## Phase 4: Implement `database.py`

Implement:

1. app-data-path discovery,
2. connection factory,
3. schema version table,
4. version 1 schema,
5. row-to-dataclass conversion,
6. settings operations,
7. task operations,
8. thought-journal operations,
9. progress query,
10. export ZIP,
11. delete-all transaction.

Use a temporary database path in tests.

Run:

```powershell
python -m unittest tests.test_database -v
```

## Phase 5: Create a minimal application shell

In `app.py`:

1. start Flet with an async `main(page)` entry point,
2. configure title, theme, padding, and adaptive behaviour,
3. initialize the database,
4. create centralized routes,
5. build bottom navigation,
6. add a global Human Help route,
7. show onboarding when disclaimer acknowledgement is missing.

Run:

```powershell
flet run app.py
```

Verify navigation before building forms.

## Phase 6: Implement Human Help first

Build:

- disclaimer,
- trusted-person card,
- counsellor card,
- Tele-MANAS card,
- Settings link,
- URL/dialler launcher.

This screen is implemented first because other forms depend on it for safety
redirects.

## Phase 7: Implement Settings and onboarding

Add:

- disclaimer acknowledgement,
- editable support contacts,
- phone validation,
- export,
- delete-all confirmation.

Test first launch and reopening.

## Phase 8: Implement tasks

Add:

- task form,
- task list,
- date and track filters,
- edit,
- completion dialog,
- reopening,
- deletion,
- evidence creation.

Prevent duplicate inserts from repeated taps.

## Phase 9: Implement Thought Journal

Add:

- structured fields,
- validation,
- safety interception,
- deterministic response preview,
- explicit save,
- journal history.

Confirm that unmatched placement-fear text creates a grounded response and
matched crisis language redirects without saving.

## Phase 10: Implement Reset Now

Add the five steps:

1. breathing,
2. five visible things,
3. frightening thought,
4. facts and prediction,
5. ten-minute action.

Keep the flow in memory. Only a user-selected task is stored.

## Phase 11: Implement progress

Use the database query result to construct a Pandas DataFrame.

Calculate:

- completed tasks per day,
- completed tasks per track,
- estimated minutes,
- 7-day and 30-day ranges.

Render with Flet Charts. Test an empty database and a database containing tasks
across multiple dates.

## Phase 12: Add assets and package metadata

Create:

- a square application icon,
- Android icon,
- iOS icon without transparency,
- optional splash graphic.

Configure `pyproject.toml`:

- app name,
- bundle ID `com.atnik.resetpath`,
- icons,
- dependencies,
- Python version,
- Android `allowBackup = "false"`.

Do not request contacts, location, microphone, camera, or storage permissions.

## Phase 13: Run the full test suite

```powershell
python -m unittest discover -s tests -v
```

Then run the desktop app:

```powershell
flet run app.py
```

Manually verify every user flow before building the APK.

## Phase 14: Build and verify Android

```powershell
flet doctor
flet build apk
```

The first build may download Flutter, Java, and Android tools.

After a successful build:

1. locate the APK under `build/apk/`,
2. copy it to `dist/ResetPath.apk`,
3. calculate its SHA-256 checksum,
4. install it on a physical phone,
5. test with internet disabled,
6. test persistence after reboot.

## Phase 15: Final documentation and release

Update the root README with:

- final dependency versions,
- tested Android model/version,
- exact artifact location,
- screenshots,
- known limitations,
- safety sources,
- and build date.

For a portfolio release, tag the source version but distribute the APK through a
release page rather than committing the binary to normal Git history.
