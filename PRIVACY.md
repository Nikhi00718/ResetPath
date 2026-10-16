# ResetPath Privacy Notes

Last updated: 16 October 2026 (version 1.0.0)

ResetPath is a local-first personal app. It has no account system, backend,
analytics SDK, advertising SDK, or cloud database. The app has no network
access: the Android shell blocks every request that is not for its own bundled
files.

## Data stored on the device

Stored in the app's private WebView storage:

- tasks, their track and day, and when you completed them;
- habits and daily habit counts;
- one mood value per day;
- focus sessions (day, minutes, linked task);
- journal pages;
- sound mix volumes and settings, including your name and trusted contact.

The storage is private to the app but not additionally encrypted. Your phone
lock screen and device encryption remain important.

## Sound

All ambient sound is synthesized on the device. ResetPath does not use the
microphone and does not record audio.

## Notifications

ResetPath asks for notification permission so it can show that sound is
playing (Android requires this for background playback) and tell you when a
focus block ends. Declining permission does not affect any other feature.

## Backup, restore, and deletion

**Save backup** writes a JSON file to a location you choose. That file contains
everything listed above and is outside ResetPath's control after you save it.
**Restore backup** replaces the app's data with the file's contents.
**Delete everything** clears the app's storage. It cannot delete backups you
saved elsewhere.

## Upgrading from 0.1 or 0.2

On the first launch after installing over the old Python build, ResetPath reads
the old local database once (read-only) and copies over tasks, diary pages,
reflections, the trusted contact, and the theme. Wearable readings and mood
check-ins from 0.2 are not imported. The old database file stays in the app's
private storage until you uninstall the app.

## Human support

Explicit self-harm language in the reset flow or journal shows human-support
options. This matching can miss language and must never be treated as evidence
that a person is safe.
