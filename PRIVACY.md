# ResetPath Privacy Notes

Last updated: 25 July 2026

ResetPath v0.1 is a local-first personal testing application. It has no
ResetPath account system, analytics SDK, advertising SDK, remote journal API,
or cloud database.

## Data stored on the device

The private SQLite database can contain:

- task titles, dates, completion notes, and evidence statements;
- journal thoughts, selected emotions, grounded responses, and next actions;
- trusted-person and campus-support details;
- optional mood, energy, and note check-ins;
- optional imported sleep, resting-heart-rate, HRV, and step readings.

The database is stored in the application's private data directory and is not
additionally encrypted. Android device encryption, a screen lock, and careful
handling of exported ZIP files remain important.

## Voice typing

ResetPath does not record or store microphone audio. A standard text field can
receive dictation from the user's phone keyboard. The keyboard provider—not
ResetPath—controls audio processing, network use, and retention. Users who need
offline dictation should check their keyboard settings before speaking.

## Wearable imports

CSV and JSON files are parsed locally. ResetPath stores only supported fields
and rejects oversized or out-of-range rows. Wearable data is displayed as
personal context and is never used for a diagnosis, safety decision, or
automated stress score.

Direct Health Connect access is not enabled in v0.1, so this release does not
request Android health permissions.

## Export and deletion

The user can export tasks, journal entries, mood check-ins, and wearable
context as CSV files inside one ZIP archive. Exported files may contain
sensitive information and are outside ResetPath's control.

**Delete all local data** removes the app's SQLite records using secure deletion
and database vacuuming. It cannot delete copies the user previously exported.

## Human support

Explicit self-harm language triggers a deterministic support redirect. This
matching can miss language and must never be treated as evidence that a person
is safe.
