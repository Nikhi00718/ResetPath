# ResetPath Testing, Privacy, and Roadmap

## 1. Automated tests

Use Python’s built-in `unittest` framework.

Run all tests:

```powershell
python -m unittest discover -s tests -v
```

### Logic tests

Test:

- whitespace and punctuation normalization,
- uppercase/lowercase handling,
- smart apostrophes,
- crisis phrase families,
- ordinary placement-anxiety statements,
- grounded-response output,
- evidence generation,
- task validation,
- input-length boundaries.

Assertions for matched crisis language:

- no grounded response is created,
- no text is returned for storage,
- the result requests Human Help navigation.

### Database tests

Use a new temporary database for each test.

Test:

- schema creation,
- reopening,
- schema version,
- settings create/update,
- task CRUD,
- completion and reopening,
- evidence statements,
- thought entry saving,
- filters,
- progress rows,
- export archive contents,
- delete-all transaction,
- quote and Unicode handling.

Tests must never read or modify the real personal database.

### Progress tests

Create tasks across different dates and tracks.

Confirm:

- seven-day range,
- thirty-day range,
- all-time range,
- counts per track,
- estimated-minute totals,
- empty data handling,
- incomplete tasks excluded from completion charts.

## 2. Manual desktop testing

Verify:

- first launch,
- skipped optional contacts,
- reopening onboarding,
- every route,
- long text wrapping,
- keyboard interaction,
- form validation,
- duplicate-tap prevention,
- database error messages,
- export cancellation,
- deletion cancellation.

## 3. Manual Android testing

On a physical phone:

1. Turn off internet access.
2. Launch ResetPath.
3. Create tasks in all four tracks.
4. Complete tasks and add reflections.
5. Force-close and reopen the app.
6. Restart the phone.
7. Confirm data remains.
8. Test a normal thought-journal entry.
9. Test a crisis phrase and confirm it is not saved.
10. Test trusted-person and counsellor buttons.
11. Test Tele-MANAS dialler and website actions.
12. Export and inspect both CSV files.
13. Cancel deletion.
14. Complete confirmed deletion.
15. Confirm onboarding returns.

## 4. Privacy model

Version 1 provides:

- app-private local SQLite storage,
- no account,
- no analytics,
- no advertisements,
- no LLM,
- no remote API,
- no application-controlled cloud sync,
- Android backup disabled in package configuration.

Version 1 does not provide:

- encrypted SQLite,
- medical-grade security,
- regulatory compliance,
- protection from somebody using an unlocked phone,
- control over copies exported by the user.

The app must describe itself as “local-first” or “stored on this device,” not
“perfectly secure.”

## 5. Data lifecycle

### Creation

Data is created only after an explicit save or task action.

### Storage

Data remains in the app-private database. Reset-session grounding text is kept
only in memory.

### Export

Tasks and thought entries may be exported as CSV files in one ZIP archive.
Contact settings are excluded.

### Deletion

Delete All Data removes database rows and settings after typed confirmation.
The app cannot remove files that were previously exported.

### Uninstall

Uninstalling normally removes local app data. The documentation must advise
exporting first if the user wants a backup.

## 6. Security checklist

- Parameterized SQL only.
- No secrets in Git.
- No signing keys in Git.
- No journal text in logs.
- No unnecessary Android permissions.
- HTTPS for external websites.
- `tel:` links open the dialler rather than silently calling.
- Input length limits.
- Transactional writes.
- Controlled database-error messages.
- Dependency versions pinned after verification.

## 7. Version 1 acceptance criteria

Version 1 is complete when:

- automated tests pass,
- the desktop app runs,
- the Android APK builds,
- the APK installs on a physical phone,
- ordinary use works offline,
- data persists after restart and reboot,
- crisis text is not saved or reframed,
- Human Help is always accessible,
- export works,
- delete-all works only after confirmation,
- no social comparison exists,
- no diagnosis or treatment claim exists.

## 8. Portfolio presentation

The GitHub repository should include:

- a clear problem statement,
- architecture diagram,
- screenshots using fictional data,
- database schema,
- safety and privacy limitations,
- test instructions,
- APK build instructions,
- a short demonstration video,
- and a roadmap.

Never publish screenshots containing real journal entries, phone numbers, or
counsellor information.

Useful portfolio topics:

- local-first architecture,
- safety-aware product design,
- deterministic NLP rules,
- SQLite schema and migrations,
- Pandas aggregation,
- cross-platform packaging,
- automated testing,
- and privacy trade-offs.

## 9. Future AI roadmap

Do not add AI until the non-AI version is stable.

If an LLM is added:

- make it optional and disabled by default,
- require approval before each remote submission,
- explain that selected text leaves the device,
- run local crisis interception first,
- never ask the LLM to decide whether a user is safe,
- never send flagged content for a safety classification,
- prohibit diagnosis and treatment advice,
- retain the deterministic converter,
- keep API keys out of the distributed mobile app.

A safe future architecture would use a small authenticated backend so the
provider key is not embedded in the APK. That backend would receive only the
specific entry the user chooses to submit. It would not receive the entire local
journal.

## 10. Out-of-scope items

Not included in version 1:

- diagnosis,
- therapy replacement,
- risk scoring,
- passive monitoring,
- background contact notification,
- social accounts,
- leaderboards,
- cloud journal sync,
- public student pilot,
- Play Store or App Store publication,
- LLM integration.

Version 0.1 does include user-initiated local wearable-file import and mood
check-ins. It still excludes passive/background monitoring and direct Health
Connect access.
