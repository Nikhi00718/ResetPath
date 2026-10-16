# ResetPath release notes

## 1.0.0 — Lightweight daily companion

A rewrite from Python/Flet to an offline web app inside a small native Android
shell. The APK went from about 117 MB to about 300 KB.

### Added

- **Ambient sound mixer** with ten generated sounds (rain, ocean, stream, wind,
  fire, night, fan, white, pink, and brown noise), presets, master volume, a
  sleep timer with a one-minute fade, and playback with the screen off. It
  also has a mini player on every tab.
- **Focus timer**: Pomodoro blocks linked to a task, with optional sound,
  chime, vibration, a notification, keep-screen-on, and session history.
- **Daily habits** with per-day counters, editable list, and a five-week heatmap.
- **One-tap mood check-in** and a two-week mood strip.
- **Guided breathing** with three patterns and haptic phase changes.
- **3D motion**: a three.js orb and particle field that breathes, reacts to
  sound, pulses on completions, and shows timer progress. Motion can be set to
  Full, Low, or Off.
- Carry-over of unfinished tasks, a "Personal" track, journal prompts, and
  JSON backup and restore.
- Automatic import of tasks, diary pages, reflections, the trusted contact, and
  the theme from the 0.1/0.2 database when installed over the old app.

### Changed

- The five-step reset is now a four-step, 2-minute reset (look around, name
  the thought, steadier view, one next step), and it can add the step to today
  or start a 10-minute focus on it.
- Daily progress, journal, and evidence are now organized as Today, Focus,
  Sounds, Calm, and You.

### Removed

- Local emotion router and opt-in diary retrieval (476 KB model, little daily value).
- Wearable CSV/JSON import and the Health Connect information screen.
- pandas, flet-charts, and the Python runtime.
- Large background artwork and duplicate icon sets.

### Safety boundaries kept

- Deterministic crisis-language check in the reset flow and the journal, which
  shows human-support options (Tele-MANAS 14416 and the trusted contact).
- No diagnosis, scoring, or generated crisis response. No streaks that can be
  lost, and no leaderboards.

### Not yet verified

- Not tested on a physical phone yet. The app was exercised in a browser at
  phone size and the APK was built and signature-verified. Background audio,
  notifications, file save and open, and the in-place upgrade import still need
  a device check.

## 0.2.0 — Local context and privacy release

Freeform diary, optional local diary context, offline emotion router, theme
preference, improved back navigation. Python/Flet build.

## 0.1.0 — First private Android release

Reset flow, tasks, evidence, meditation, local support cards, wearable-file
import, and Android build. Python/Flet build.
