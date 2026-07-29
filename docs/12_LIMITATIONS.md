# Limitations and release readiness

This page is deliberately direct about what ResetPath v0.2.0 can and cannot do.

## Works in this release

- Private local tasks, evidence, diary writing, reflections, export, and
  delete-all controls.
- Deterministic crisis-language redirect to human-help information.
- Optional local retrieval of selected diary excerpts for one reflection.
- Offline broad-emotion routing with a confidence abstention path.
- Light/dark appearance, animated reset and meditation, and supported haptics.
- Manual CSV/JSON wearable-file import and optional mood/energy logging.
- Android APKs for ARM64, ARMv7, and x86_64 devices.

## Not available yet

| Area | Current limitation | What is needed before it can ship |
| --- | --- | --- |
| Samsung Health | No direct integration. | Samsung SDK access, partner/package registration, native Android bridge, permission and device testing. |
| Google Fit / Health Connect | No direct connection. | A native Android bridge, explicit Health Connect permissions, rationale screen, revoke/delete tests, and Play declarations. |
| Voice button | Keyboard dictation only. | User-tapped microphone permission, native local transcription, editable draft, and deletion of temporary audio. |
| Home-screen widget | Not included. | Native Android `AppWidgetProvider`, privacy-safe lock-screen design, and device tests. |
| Cloud backup / multi-device sync | Not included. | A consented backend, encryption design, authentication, deletion workflow, and privacy review. |
| Production distribution | Debug-signed APK, not a Play Store listing. | Production keystore, versioning policy, Play App Bundle, policy declarations, testing, and signing verification. |

## AI boundaries

The local router was trained only on a public general-emotion dataset. It is
not trained on private ResetPath content, and it has no clinical evaluation.
It can be wrong, should be ignored when it does not fit, and never has final
say over the user’s emotion or next step.

ResetPath does not contain an autonomous agent that can message people, make
appointments, make health decisions, assess suicide risk, or diagnose a
condition. The crisis-language route always points toward human support rather
than asking an AI to make a safety judgement.

## Testing status

Automated unit checks cover local storage, migrations, safe retrieval, data
export/delete behaviour, wearable-file parsing, and core flows. The v0.2 local
emotion artifact was evaluated on held-out public data; see
[emotion-router-evaluation.json](emotion-router-evaluation.json).

The build has been packaged and inspected, but it has not been tested on every
Android model. Before any broad release, test install, navigation, storage,
offline use, keyboard, haptics, theme switching, export, and deletion on real
target devices.

## Version history

### v0.2.0 — Local context and privacy

Added the freeform diary, opt-in local diary context, locally packaged emotion
router, persistent themes, route-aware back navigation, and model evaluation.
The main limitation remains that it is a broad non-clinical classifier and the
health integrations are still planned.

### v0.1.0 — Foundation release

Added Reset now, placement tasks, evidence, visual meditation, reviewed support
cards, keyboard dictation, wearable-file import, mood check-ins, haptics, and
Android packaging. The main limitations were lack of a freeform diary,
no local model, and no direct health connection.
