# ResetPath production readiness and device roadmap

This document separates what ResetPath can honestly ship now from work that
requires native Android code, approvals, or evaluation. The app is a personal
wellbeing and study-support tool. It is not a medical device and must never
diagnose, predict safety, or tell someone to ignore professional support.

## Implemented in the next app build

- Android back returns to the previous ResetPath screen before Android may exit
  the app.
- Light and dark themes are stored on the device.
- The Journal tab is a free-form private diary page. It is not automatically
  analysed. Pages can be reopened, edited, exported, and deleted with the rest
  of local data.
- The optional guided thought flow remains separate from diary writing.
- Voice typing is available in any writing field through the phone keyboard;
  ResetPath receives only the text, not an audio recording.

## Health data: safe, realistic connection plan

The first direct connector should target **Android Health Connect**, not the
retired Google Fit Android APIs. It can read user-approved sleep, aggregated
steps, resting heart rate, and HRV records in a foreground-only manual refresh.
Health Connect aggregates cumulative step data, which avoids double-counting
when several apps contribute records. ResetPath must show source, date range,
and a disconnect/delete option.

The app must request only the fields the person enables. The Health Connect
privacy rationale must explain that the data stays on-device, is used as
descriptive context, and does not create a stress or mental-health score.

Samsung Health needs a separate native SDK integration. Samsung requires
developer/partner registration of the final package name and signing SHA-256
for public distribution. Samsung Health Data SDK support also requires Android
10+ and Samsung Health. Therefore it cannot be advertised as connected in the
current APK.

Suggested next implementation sequence:

1. Create a Kotlin Android native extension for Flet.
2. Add Health Connect availability and user-selected read-permission methods.
3. Add a foreground-only `Refresh health data` action.
4. Aggregate daily steps; import sleep and vital records without converting
   them into a diagnosis.
5. Test disconnect, permission denial, no-data state, deletion, and duplicate
   data sources on a physical Android phone.
6. Submit Samsung partnership details after the production signing key exists.

## Local AI: no training on private diary pages by default

There is no safe or meaningful way to train a mental-health model overnight on
one person's unlabelled diary. Doing that would be private-data training with
no consent workflow, no ground truth, no safety evaluation, and no evidence it
helps. ResetPath will not do this.

The production route is an optional, download-on-demand small local model that
uses a reviewed support-card library. It must run after the existing crisis
language gate and return only a schema with: the user's words, user-selected
emotion, uncertainty in a prediction, and one optional low-risk action. It may
not diagnose, assess risk, generate clinical advice, or automatically read
diary pages.

Before adoption, evaluate it on a consented, de-identified test set for:

- crisis-language redirect recall;
- no diagnosis or certainty claims;
- no invented facts or medical advice;
- latency, RAM use, battery use, and offline reliability;
- human review of every response template.

Until that evaluation is passed, the existing deterministic, reviewable
support-card retrieval is the production-safe local assistant.

## Voice and widget work

Phone-keyboard dictation is the only supported voice path today. A real local
voice button needs a Kotlin bridge, microphone permission only after a tap,
on-device transcription (for example a compact Whisper runtime), editable text
before saving, and immediate removal of temporary audio.

An Android home-screen widget also needs native Kotlin `AppWidgetProvider`
code. The first widget should be deliberately small: **Reset now**, **one task**,
and **open today’s diary**. It should never display diary text or health data
on the lock screen.

## Release gate

Before calling a build production ready:

1. Run unit tests and device smoke tests offline.
2. Test back navigation from every screen on a physical phone.
3. Test light/dark mode, font scaling, keyboard overlay, and screen rotation.
4. Test export, delete-all, and reinstall behaviour.
5. Verify the release APK signature and download on a phone.
6. Publish a privacy policy, Health Connect permission rationale, and support
   escalation copy.
7. Complete Google Play health-data declarations before any store listing.

## Official references

- [Android Health Connect: read data](https://developer.android.com/health-and-fitness/health-connect/read-data)
- [Android Health Connect integration overview](https://developer.android.com/health-and-fitness/guides/health-connect)
- [Samsung Health Data SDK: app creation process](https://developer.samsung.com/health/data/process.html)
- [Samsung Health Data SDK: app verification](https://developer.samsung.com/health/data/guide/app-verification.html)
